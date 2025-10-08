from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from analytics import serializers

from .models import Comment, CommentLike, CommentReport
from .serializers import (
    CommentSerializer, CommentLikeSerializer, 
    CommentReportSerializer, CommentStatsSerializer
)


class CommentPagination(PageNumberPagination):
    """
    Custom pagination for comments
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CommentListCreateView(generics.ListCreateAPIView):
    """
    List all comments and create new ones
    """
    serializer_class = CommentSerializer
    pagination_class = CommentPagination
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """
        Get active comments with optional filtering
        """
        queryset = Comment.objects.filter(is_active=True)
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(content__icontains=search) | Q(author__icontains=search)
            )
        
        # Filter by author
        author = self.request.query_params.get('author', None)
        if author:
            queryset = queryset.filter(author__icontains=author)
        
        # Date filtering
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """
        Create comment with rate limiting
        """
        # Simple rate limiting - max 5 comments per IP per hour
        ip_address = self.get_client_ip()
        cache_key = f'comment_rate_limit_{ip_address}'
        
        current_count = cache.get(cache_key, 0)
        if current_count >= 5:
            raise serializers.ValidationError(
                "Rate limit exceeded. Please wait before posting another comment."
            )
        
        # Save the comment
        comment = serializer.save()
        
        # Update rate limit counter
        cache.set(cache_key, current_count + 1, 3600)  # 1 hour
    
    def get_client_ip(self):
        """
        Get client IP address
        """
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific comment
    """
    queryset = Comment.objects.filter(is_active=True)
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_permissions(self):
        """
        Only allow safe methods for non-owners
        """
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()
    
    def perform_destroy(self, instance):
        """
        Soft delete instead of hard delete
        """
        instance.is_active = False
        instance.save()


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def toggle_comment_like(request, comment_id):
    """
    Toggle like for a comment
    """
    comment = get_object_or_404(Comment, id=comment_id, is_active=True)
    
    # Get client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Check if already liked
    like, created = CommentLike.objects.get_or_create(
        comment=comment,
        ip_address=ip_address,
        defaults={
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'user': request.user if request.user.is_authenticated else None
        }
    )
    
    if not created:
        # Toggle the like
        like.is_active = not like.is_active
        like.save()
    
    return Response({
        'liked': like.is_active,
        'likes_count': comment.likes_count,
        'message': 'Like toggled successfully'
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def report_comment(request, comment_id):
    """
    Report a comment for moderation
    """
    comment = get_object_or_404(Comment, id=comment_id, is_active=True)
    
    serializer = CommentReportSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save(comment=comment)
        return Response({
            'message': 'Comment reported successfully. Thank you for helping us maintain quality.'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@cache_page(60 * 15)  # Cache for 15 minutes
def comment_stats(request):
    """
    Get comment statistics
    """
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Basic stats
    total_comments = Comment.objects.filter(is_active=True).count()
    total_likes = CommentLike.objects.filter(is_active=True).count()
    comments_today = Comment.objects.filter(
        is_active=True, created_at__date=today
    ).count()
    comments_this_week = Comment.objects.filter(
        is_active=True, created_at__gte=week_ago
    ).count()
    comments_this_month = Comment.objects.filter(
        is_active=True, created_at__gte=month_ago
    ).count()
    
    # Top authors
    top_authors = Comment.objects.filter(
        is_active=True
    ).values('author').annotate(
        comment_count=Count('id')
    ).order_by('-comment_count')[:5]
    
    # Recent activity (last 24 hours)
    recent_activity = Comment.objects.filter(
        is_active=True,
        created_at__gte=now - timedelta(hours=24)
    ).values(
        'author', 'created_at', 'content'
    ).order_by('-created_at')[:10]
    
    # Format recent activity
    formatted_activity = []
    for activity in recent_activity:
        formatted_activity.append({
            'author': activity['author'],
            'time': activity['created_at'],
            'preview': activity['content'][:50] + '...' if len(activity['content']) > 50 else activity['content']
        })
    
    stats_data = {
        'total_comments': total_comments,
        'total_likes': total_likes,
        'comments_today': comments_today,
        'comments_this_week': comments_this_week,
        'comments_this_month': comments_this_month,
        'top_authors': list(top_authors),
        'recent_activity': formatted_activity
    }
    
    serializer = CommentStatsSerializer(stats_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Simple health check endpoint
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now(),
        'version': '1.0.0'
    })
