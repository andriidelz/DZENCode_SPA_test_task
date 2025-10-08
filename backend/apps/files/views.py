from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from django.http import HttpResponse, Http404
from django.core.cache import cache
from django.db.models import Sum, Count, Avg
from datetime import timedelta
from django.utils import timezone

from .models import UploadedFile, ImageFile, TextFile
from .serializers import (
    UploadedFileSerializer,
    ImageFileSerializer,
    TextFileSerializer,
    FileUploadSerializer,
    FileStatsSerializer,
    BulkFileUploadSerializer
)
from .services import FileUploadService, FileCleanupService


class FilePagination(PageNumberPagination):
    """Custom pagination for files"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class FileUploadView(generics.CreateAPIView):
    """
    Upload a single file
    """
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='20/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited file upload"""
        return super().post(request, *args, **kwargs)
    
    @extend_schema(
        summary="Upload file",
        description="Upload a single image or text file with automatic processing"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BulkFileUploadView(generics.CreateAPIView):
    """
    Upload multiple files at once
    """
    serializer_class = BulkFileUploadSerializer
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited bulk file upload"""
        return super().post(request, *args, **kwargs)
    
    @extend_schema(
        summary="Bulk upload files",
        description="Upload multiple files at once (max 10 files)"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class FileListView(generics.ListAPIView):
    """
    List uploaded files with filtering
    """
    serializer_class = UploadedFileSerializer
    pagination_class = FilePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['file_type', 'status']
    search_fields = ['original_name']
    ordering_fields = ['created_at', 'file_size', 'original_name']
    ordering = ['-created_at']
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return UploadedFile.objects.filter(status='completed')
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="List files",
        description="Get a paginated list of uploaded files with filtering options"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FileDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific file
    """
    queryset = UploadedFile.objects.filter(status='completed')
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        obj = self.get_object()
        if obj.file_type == 'image' and hasattr(obj, 'image_metadata'):
            return ImageFileSerializer
        elif obj.file_type == 'text' and hasattr(obj, 'text_metadata'):
            return TextFileSerializer
        return UploadedFileSerializer
    
    def get_object(self):
        obj = super().get_object()
        if obj.file_type == 'image' and hasattr(obj, 'image_metadata'):
            return obj.image_metadata
        elif obj.file_type == 'text' and hasattr(obj, 'text_metadata'):
            return obj.text_metadata
        return obj
    
    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Get file details",
        description="Get detailed information about a specific file including metadata"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FileDownloadView(generics.RetrieveAPIView):
    """
    Download a file
    """
    queryset = UploadedFile.objects.filter(status='completed')
    permission_classes = [permissions.AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        """Return file for download"""
        file_obj = self.get_object()
        
        try:
            # Open and return file
            with open(file_obj.file.path, 'rb') as f:
                response = HttpResponse(
                    f.read(),
                    content_type=file_obj.mime_type or 'application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{file_obj.original_name}"'
                response['Content-Length'] = file_obj.file_size
                return response
        
        except FileNotFoundError:
            raise Http404("File not found")
    
    @extend_schema(
        summary="Download file",
        description="Download the actual file content"
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


@extend_schema(
    summary="Get file statistics",
    description="Get statistics about uploaded files"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@cache_page(60 * 10)  # Cache for 10 minutes
def file_stats(request):
    """
    Get file upload statistics
    """
    cache_key = 'file_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Calculate statistics
        total_files = UploadedFile.objects.filter(status='completed').count()
        total_size = UploadedFile.objects.filter(status='completed').aggregate(
            total=Sum('file_size')
        )['total'] or 0
        
        # Files by type
        files_by_type = dict(
            UploadedFile.objects.filter(status='completed').values('file_type').annotate(
                count=Count('id')
            ).values_list('file_type', 'count')
        )
        
        # Files this week
        week_ago = timezone.now() - timedelta(days=7)
        files_this_week = UploadedFile.objects.filter(
            status='completed',
            created_at__gte=week_ago
        ).count()
        
        # Average file size
        avg_size = UploadedFile.objects.filter(status='completed').aggregate(
            avg=Avg('file_size')
        )['avg'] or 0
        
        # Largest file
        largest_file_obj = UploadedFile.objects.filter(status='completed').order_by('-file_size').first()
        largest_file = None
        if largest_file_obj:
            largest_file = {
                'name': largest_file_obj.original_name,
                'size': largest_file_obj.file_size,
                'type': largest_file_obj.file_type
            }
        
        # Most recent upload
        recent_file_obj = UploadedFile.objects.filter(status='completed').order_by('-created_at').first()
        most_recent_upload = None
        if recent_file_obj:
            most_recent_upload = {
                'name': recent_file_obj.original_name,
                'uploaded_at': recent_file_obj.created_at,
                'type': recent_file_obj.file_type
            }
        
        # Format total size
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        
        stats = {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_display': format_size(total_size),
            'files_by_type': files_by_type,
            'files_this_week': files_this_week,
            'average_file_size': avg_size,
            'largest_file': largest_file,
            'most_recent_upload': most_recent_upload
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, stats, 60 * 10)
    
    serializer = FileStatsSerializer(stats)
    return Response(serializer.data)


@extend_schema(
    summary="Cleanup old files",
    description="Clean up files older than specified days (admin only)"
)
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def cleanup_files(request):
    """
    Clean up old files (admin endpoint)
    """
    days = request.data.get('days', 30)
    
    try:
        days = int(days)
        if days < 1:
            return Response(
                {'error': 'Days must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid days parameter'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Clean up old files
    deleted_count = FileCleanupService.cleanup_old_files(days)
    
    # Clean up failed uploads
    failed_deleted = FileCleanupService.cleanup_failed_uploads()
    
    return Response({
        'message': f'Cleanup completed',
        'deleted_files': deleted_count,
        'deleted_failed_uploads': failed_deleted
    })


@extend_schema(
    summary="Get file thumbnail",
    description="Get thumbnail for image files"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def file_thumbnail(request, file_id):
    """
    Get thumbnail for image file
    """
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id, status='completed')
        
        if uploaded_file.file_type != 'image':
            return Response(
                {'error': 'File is not an image'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(uploaded_file, 'image_metadata'):
            return Response(
                {'error': 'Image metadata not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        image_data = uploaded_file.image_metadata
        
        if not image_data.thumbnail:
            return Response(
                {'error': 'Thumbnail not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return thumbnail file
        try:
            with open(image_data.thumbnail.path, 'rb') as f:
                response = HttpResponse(
                    f.read(),
                    content_type='image/jpeg'
                )
                response['Cache-Control'] = 'public, max-age=86400'  # Cache for 1 day
                return response
        
        except FileNotFoundError:
            return Response(
                {'error': 'Thumbnail file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    except UploadedFile.DoesNotExist:
        return Response(
            {'error': 'File not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    summary="Get file preview",
    description="Get preview for text files"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def file_preview(request, file_id):
    """
    Get preview for text file
    """
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id, status='completed')
        
        if uploaded_file.file_type != 'text':
            return Response(
                {'error': 'File is not a text file'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not hasattr(uploaded_file, 'text_metadata'):
            return Response(
                {'error': 'Text metadata not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        text_data = uploaded_file.text_metadata
        
        return Response({
            'preview': text_data.preview,
            'encoding': text_data.encoding,
            'line_count': text_data.line_count,
            'word_count': text_data.word_count,
            'character_count': text_data.character_count
        })
    
    except UploadedFile.DoesNotExist:
        return Response(
            {'error': 'File not found'},
            status=status.HTTP_404_NOT_FOUND
        )
