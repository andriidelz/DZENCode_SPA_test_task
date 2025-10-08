from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import FileUpload, FileThumbnail, FileDownload
from .serializers import (
    FileUploadSerializer, FileUploadCreateSerializer,
    FileDownloadSerializer, FileStatsSerializer
)
from files import serializers


class FilePagination(PageNumberPagination):
    """
    Custom pagination for files
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class FileUploadListCreateView(generics.ListCreateAPIView):
    """
    List all files and upload new ones
    """
    pagination_class = FilePagination
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        """Use different serializers for different methods"""
        if self.request.method == 'POST':
            return FileUploadCreateSerializer
        return FileUploadSerializer
    
    def get_queryset(self):
        """Get files based on filters"""
        queryset = FileUpload.objects.filter(is_active=True)
        
        # Public filter
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        
        # File type filter
        file_type = self.request.query_params.get('type', None)
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        # Search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # User filter (for authenticated users)
        if self.request.user.is_authenticated:
            user_only = self.request.query_params.get('user_only', None)
            if user_only:
                queryset = queryset.filter(uploaded_by=self.request.user)
        
        return queryset.order_by('-uploaded_at')
    
    def perform_create(self, serializer):
        """Create file with rate limiting"""
        # Simple rate limiting - max 10 uploads per IP per hour
        ip_address = self.get_client_ip()
        cache_key = f'file_upload_rate_limit_{ip_address}'
        
        current_count = cache.get(cache_key, 0)
        if current_count >= 10:
            raise serializers.ValidationError(
                "Upload rate limit exceeded. Please wait before uploading more files."
            )
        
        # Save the file
        file_upload = serializer.save()
        
        # Update rate limit counter
        cache.set(cache_key, current_count + 1, 3600)  # 1 hour
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class FileUploadDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific file
    """
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Get files based on permissions"""
        queryset = FileUpload.objects.filter(is_active=True)
        
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        
        return queryset
    
    def get_permissions(self):
        """Only allow owners or staff to modify files"""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()
    
    def perform_update(self, serializer):
        """Only allow owner to update"""
        file_upload = self.get_object()
        if file_upload.uploaded_by != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only edit your own files.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Soft delete instead of hard delete"""
        if instance.uploaded_by != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only delete your own files.")
        instance.is_active = False
        instance.save()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def download_file(request, file_id):
    """
    Download a file and track the download
    """
    file_upload = get_object_or_404(
        FileUpload, 
        id=file_id, 
        is_active=True
    )
    
    # Check permissions
    if not file_upload.is_public and not request.user.is_authenticated:
        raise Http404("File not found")
    
    # Track download
    FileDownload.objects.create(
        file_upload=file_upload,
        downloaded_by=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referer=request.META.get('HTTP_REFERER', '')
    )
    
    # Serve file
    try:
        response = HttpResponse(
            file_upload.file.read(),
            content_type=file_upload.mime_type or 'application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{file_upload.name}"'
        response['Content-Length'] = file_upload.file_size
        return response
    except Exception as e:
        raise Http404("File not found")


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_thumbnail(request, file_id, size='medium'):
    """
    Get thumbnail for an image file
    """
    file_upload = get_object_or_404(
        FileUpload,
        id=file_id,
        is_active=True,
        file_type='image'
    )
    
    # Check permissions
    if not file_upload.is_public and not request.user.is_authenticated:
        raise Http404("File not found")
    
    # Get or create thumbnail
    thumbnail, created = FileThumbnail.objects.get_or_create(
        file_upload=file_upload,
        size=size,
        defaults={'size': size}
    )
    
    if thumbnail.thumbnail:
        try:
            response = HttpResponse(
                thumbnail.thumbnail.read(),
                content_type='image/jpeg'
            )
            response['Content-Length'] = thumbnail.thumbnail.size
            return response
        except Exception as e:
            raise Http404("Thumbnail not found")
    
    raise Http404("Thumbnail not available")


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@cache_page(60 * 15)  # Cache for 15 minutes
def file_stats(request):
    """
    Get file statistics
    """
    # Basic stats
    total_files = FileUpload.objects.filter(is_active=True).count()
    total_size = FileUpload.objects.filter(is_active=True).aggregate(
        total=Sum('file_size')
    )['total'] or 0
    total_downloads = FileDownload.objects.count()
    
    # Files by type
    files_by_type = dict(
        FileUpload.objects.filter(is_active=True).values('file_type').annotate(
            count=Count('id')
        ).values_list('file_type', 'count')
    )
    
    # Recent uploads (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_uploads = FileUpload.objects.filter(
        is_active=True,
        uploaded_at__gte=week_ago
    ).values(
        'name', 'file_type', 'uploaded_at', 'uploaded_by__username'
    ).order_by('-uploaded_at')[:10]
    
    # Popular files (most downloaded)
    popular_files = FileUpload.objects.filter(
        is_active=True
    ).annotate(
        download_count=Count('downloads')
    ).filter(
        download_count__gt=0
    ).order_by('-download_count')[:10]
    
    popular_files_data = []
    for file_obj in popular_files:
        popular_files_data.append({
            'id': file_obj.id,
            'name': file_obj.name,
            'file_type': file_obj.file_type,
            'download_count': file_obj.download_count,
            'uploaded_at': file_obj.uploaded_at
        })
    
    stats_data = {
        'total_files': total_files,
        'total_size': total_size,
        'total_downloads': total_downloads,
        'files_by_type': files_by_type,
        'recent_uploads': list(recent_uploads),
        'popular_files': popular_files_data
    }
    
    serializer = FileStatsSerializer(stats_data)
    return Response(serializer.data)


def get_client_ip(request):
    """
    Helper function to get client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
