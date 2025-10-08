from datetime import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q, Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Comment, CommentLike, CaptchaToken
from .serializers import (
    CommentSerializer,
    CommentListSerializer,
    CommentLikeSerializer,
    CaptchaSerializer
)
from .filters import CommentFilter
from .services import CommentService, CaptchaService
from apps.analytics.tasks import track_comment_event


class CommentPagination(PageNumberPagination):
    """Custom pagination for comments"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class CommentListCreateView(generics.ListCreateAPIView):
    """
    List comments with filtering and sorting, create new comments
    """
    queryset = Comment.objects.filter(is_active=True, parent__isnull=True)
    pagination_class = CommentPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CommentFilter
    search_fields = ['user_name', 'sanitized_text']
    ordering_fields = ['created_at', 'user_name', 'likes_count']
    ordering = ['-created_at']  # LIFO by default
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CommentListSerializer
        return CommentSerializer
    
    def get_queryset(self):
        """Optimized queryset with prefetch_related for better performance"""
        return Comment.objects.filter(
            is_active=True,
            parent__isnull=True
        ).select_related(
            'parent'
        ).prefetch_related(
            'files',
            Prefetch(
                'replies',
                queryset=Comment.objects.filter(is_active=True).order_by('created_at')
            )
        )
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request, *args, **kwargs):
        """Cached GET method for better performance"""
        return super().get(request, *args, **kwargs)
    
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited POST method"""
        response = super().post(request, *args, **kwargs)
        
        # Track analytics event
        if response.status_code == status.HTTP_201_CREATED:
            comment_id = response.data.get('id')
            if comment_id:
                track_comment_event.delay(
                    comment_id=comment_id,
                    event_type='created',
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
        
        return response
    
    def get_client_ip(self):
        """Extract client IP from request"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    @extend_schema(
        summary="List comments",
        description="Get a paginated list of comments with filtering and sorting options",
        parameters=[
            OpenApiParameter('ordering', OpenApiTypes.STR, description='Order by: created_at, user_name, likes_count'),
            OpenApiParameter('search', OpenApiTypes.STR, description='Search in user_name and text'),
            OpenApiParameter('user_name', OpenApiTypes.STR, description='Filter by user name'),
            OpenApiParameter('created_after', OpenApiTypes.DATETIME, description='Filter comments created after this date'),
            OpenApiParameter('created_before', OpenApiTypes.DATETIME, description='Filter comments created before this date'),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create comment",
        description="Create a new comment with CAPTCHA validation and optional file attachments"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CommentDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single comment with all its replies
    """
    queryset = Comment.objects.filter(is_active=True)
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Optimized queryset with nested replies"""
        return Comment.objects.filter(
            is_active=True
        ).select_related(
            'parent'
        ).prefetch_related(
            'files',
            'replies__files',
            'replies__replies__files'
        )
    
    @method_decorator(cache_page(60 * 2))  # Cache for 2 minutes
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CommentReplyCreateView(generics.CreateAPIView):
    """
    Create a reply to an existing comment
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='20/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited reply creation"""
        parent_id = kwargs.get('parent_id')
        
        try:
            parent_comment = Comment.objects.get(id=parent_id, is_active=True)
            if not parent_comment.can_reply:
                return Response(
                    {'error': 'Cannot reply to this comment (max nesting level reached)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Comment.DoesNotExist:
            return Response(
                {'error': 'Parent comment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Set parent in request data
        request.data['parent'] = parent_id
        
        response = super().post(request, *args, **kwargs)
        
        # Track analytics event
        if response.status_code == status.HTTP_201_CREATED:
            comment_id = response.data.get('id')
            if comment_id:
                track_comment_event.delay(
                    comment_id=comment_id,
                    event_type='reply_created',
                    parent_id=parent_id,
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
        
        return response
    
    def get_client_ip(self):
        """Extract client IP from request"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class CommentLikeCreateView(generics.CreateAPIView):
    """
    Like a comment
    """
    serializer_class = CommentLikeSerializer
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='30/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited like creation"""
        comment_id = kwargs.get('comment_id')
        
        try:
            comment = Comment.objects.get(id=comment_id, is_active=True)
        except Comment.DoesNotExist:
            return Response(
                {'error': 'Comment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Set comment in request data
        request.data['comment'] = comment_id
        
        response = super().post(request, *args, **kwargs)
        
        # Track analytics event
        if response.status_code == status.HTTP_201_CREATED:
            track_comment_event.delay(
                comment_id=comment_id,
                event_type='liked',
                ip_address=self.get_client_ip(),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return response
    
    def get_client_ip(self):
        """Extract client IP from request"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@extend_schema(
    summary="Generate CAPTCHA",
    description="Generate a new CAPTCHA challenge for comment creation"
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@ratelimit(key='ip', rate='20/m', method='POST')
def generate_captcha(request):
    """
    Generate a new CAPTCHA challenge
    """
    serializer = CaptchaSerializer(data={}, context={'request': request})
    if serializer.is_valid():
        captcha = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get CAPTCHA image",
    description="Get the image for a CAPTCHA token"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def captcha_image(request, token):
    """
    Generate and return CAPTCHA image
    """
    try:
        captcha = CaptchaToken.objects.get(token=token)
        if captcha.is_expired:
            return Response(
                {'error': 'CAPTCHA has expired'},
                status=status.HTTP_410_GONE
            )
        
        # Generate image using CaptchaService
        captcha_service = CaptchaService()
        image_data = captcha_service.generate_image(captcha.challenge)
        
        from django.http import HttpResponse
        response = HttpResponse(image_data, content_type='image/png')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
        
    except CaptchaToken.DoesNotExist:
        return Response(
            {'error': 'Invalid CAPTCHA token'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    summary="Preview comment",
    description="Preview how a comment will look after HTML sanitization"
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@ratelimit(key='ip', rate='30/m', method='POST')
def preview_comment(request):
    """
    Preview comment text after sanitization (AJAX endpoint)
    """
    text = request.data.get('text', '')
    if not text:
        return Response(
            {'error': 'Text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create temporary comment instance for sanitization
    temp_comment = Comment(text=text)
    sanitized_text = temp_comment.sanitize_text(text)
    
    return Response({
        'original_text': text,
        'sanitized_text': sanitized_text,
        'is_valid_xhtml': temp_comment.is_valid_xhtml(sanitized_text)
    })


@extend_schema(
    summary="Get comment statistics",
    description="Get statistics about comments"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@cache_page(60 * 10)  # Cache for 10 minutes
def comment_stats(request):
    """
    Get comment statistics
    """
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    
    # Use cached stats if available
    cache_key = 'comment_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        
        stats = {
            'total_comments': Comment.objects.filter(is_active=True).count(),
            'total_replies': Comment.objects.filter(is_active=True, parent__isnull=False).count(),
            'comments_this_week': Comment.objects.filter(
                is_active=True,
                created_at__gte=week_ago
            ).count(),
            'average_replies_per_comment': Comment.objects.filter(
                is_active=True,
                parent__isnull=True
            ).aggregate(avg_replies=Avg('replies_count'))['avg_replies'] or 0,
            'most_liked_comment_id': Comment.objects.filter(
                is_active=True
            ).order_by('-likes_count').values_list('id', flat=True).first(),
            'most_active_users': list(
                Comment.objects.filter(
                    is_active=True
                ).values('user_name').annotate(
                    comment_count=Count('id')
                ).order_by('-comment_count')[:5]
            )
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, stats, 60 * 10)
    
    return Response(stats)
