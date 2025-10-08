from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User

from .models import AnalyticsEvent, DailyStats, PopularContent, UserBehavior
from .serializers import (
    AnalyticsEventSerializer, DailyStatsSerializer,
    PopularContentSerializer, UserBehaviorSerializer,
    AnalyticsDashboardSerializer, RealTimeStatsSerializer
)
from comments.models import Comment, CommentLike
from files.models import FileUpload, FileDownload


class AnalyticsEventCreateView(generics.CreateAPIView):
    """
    Create analytics events
    """
    queryset = AnalyticsEvent.objects.all()
    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        """Create event and update user behavior"""
        event = serializer.save()
        
        # Update user behavior if user is authenticated
        if event.user:
            self.update_user_behavior(event)
    
    def update_user_behavior(self, event):
        """Update user behavior data based on event"""
        behavior, created = UserBehavior.objects.get_or_create(
            user=event.user,
            defaults={
                'first_activity': event.timestamp,
                'last_activity': event.timestamp
            }
        )
        
        # Update last activity
        behavior.last_activity = event.timestamp
        
        # Update specific metrics based on event type
        if event.event_type == 'comment_post':
            behavior.comments_posted += 1
        elif event.event_type == 'comment_like':
            behavior.comments_liked += 1
        elif event.event_type == 'file_upload':
            behavior.files_uploaded += 1
        elif event.event_type == 'file_download':
            behavior.files_downloaded += 1
        elif event.event_type == 'search':
            behavior.searches_performed += 1
        
        behavior.save()


class DailyStatsListView(generics.ListAPIView):
    """
    Get daily statistics
    """
    serializer_class = DailyStatsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get daily stats with date filtering"""
        queryset = DailyStats.objects.all()
        
        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                pass
        
        # Default to last 30 days if no filters
        if not start_date and not end_date:
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            queryset = queryset.filter(date__gte=thirty_days_ago)
        
        return queryset.order_by('-date')


class PopularContentListView(generics.ListAPIView):
    """
    Get popular content
    """
    serializer_class = PopularContentSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Get popular content with filtering"""
        queryset = PopularContent.objects.all()
        
        # Content type filter
        content_type = self.request.query_params.get('type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Time period filter
        period = self.request.query_params.get('period', 'all')
        if period == 'today':
            queryset = queryset.filter(views_today__gt=0).order_by('-views_today')
        elif period == 'week':
            queryset = queryset.filter(views_this_week__gt=0).order_by('-views_this_week')
        elif period == 'month':
            queryset = queryset.filter(views_this_month__gt=0).order_by('-views_this_month')
        else:
            queryset = queryset.order_by('-view_count')
        
        return queryset[:50]  # Limit to top 50


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@cache_page(60 * 10)  # Cache for 10 minutes
def analytics_dashboard(request):
    """
    Get analytics dashboard data
    """
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    # Overview stats
    total_users = User.objects.count()
    total_comments = Comment.objects.filter(is_active=True).count()
    total_files = FileUpload.objects.filter(is_active=True).count()
    total_page_views = AnalyticsEvent.objects.filter(event_type='page_view').count()
    
    # Recent activity (last 30 days)
    recent_users = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    recent_comments = Comment.objects.filter(
        is_active=True,
        created_at__gte=thirty_days_ago
    ).count()
    recent_files = FileUpload.objects.filter(
        is_active=True,
        uploaded_at__gte=thirty_days_ago
    ).count()
    recent_page_views = AnalyticsEvent.objects.filter(
        event_type='page_view',
        timestamp__gte=thirty_days_ago
    ).count()
    
    # Previous period for growth calculation
    prev_users = User.objects.filter(
        date_joined__gte=sixty_days_ago,
        date_joined__lt=thirty_days_ago
    ).count()
    prev_comments = Comment.objects.filter(
        is_active=True,
        created_at__gte=sixty_days_ago,
        created_at__lt=thirty_days_ago
    ).count()
    prev_files = FileUpload.objects.filter(
        is_active=True,
        uploaded_at__gte=sixty_days_ago,
        uploaded_at__lt=thirty_days_ago
    ).count()
    
    # Calculate growth rates
    user_growth_rate = calculate_growth_rate(recent_users, prev_users)
    comment_growth_rate = calculate_growth_rate(recent_comments, prev_comments)
    file_growth_rate = calculate_growth_rate(recent_files, prev_files)
    
    # Popular content
    popular_comments = Comment.objects.filter(
        is_active=True
    ).annotate(
        like_count=Count('likes', filter=Q(likes__is_active=True))
    ).order_by('-like_count')[:5]
    
    popular_files = FileUpload.objects.filter(
        is_active=True
    ).annotate(
        download_count=Count('downloads')
    ).order_by('-download_count')[:5]
    
    # Popular search terms
    popular_search_terms = AnalyticsEvent.objects.filter(
        event_type='search',
        timestamp__gte=thirty_days_ago
    ).values('properties__query').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Daily activity (last 7 days)
    seven_days_ago = now - timedelta(days=7)
    daily_stats = DailyStats.objects.filter(
        date__gte=seven_days_ago.date()
    ).order_by('date')
    
    daily_activity = []
    for stat in daily_stats:
        daily_activity.append({
            'date': stat.date,
            'comments': stat.comments_count,
            'users': stat.active_users_count,
            'files': stat.files_uploaded_count,
            'page_views': stat.page_views_count
        })
    
    # Top users by engagement
    top_users = UserBehavior.objects.exclude(
        user__username='admin'
    ).order_by('-engagement_score')[:10]
    
    top_users_data = []
    for behavior in top_users:
        top_users_data.append({
            'username': behavior.user.username,
            'engagement_score': behavior.engagement_score,
            'comments_posted': behavior.comments_posted,
            'files_uploaded': behavior.files_uploaded,
            'last_activity': behavior.last_activity
        })
    
    # System health metrics
    error_events = AnalyticsEvent.objects.filter(
        event_type='error',
        timestamp__gte=thirty_days_ago
    ).count()
    total_events = AnalyticsEvent.objects.filter(
        timestamp__gte=thirty_days_ago
    ).count()
    
    error_rate = (error_events / total_events * 100) if total_events > 0 else 0
    
    dashboard_data = {
        'total_users': total_users,
        'total_comments': total_comments,
        'total_files': total_files,
        'total_page_views': total_page_views,
        'recent_users': recent_users,
        'recent_comments': recent_comments,
        'recent_files': recent_files,
        'recent_page_views': recent_page_views,
        'user_growth_rate': user_growth_rate,
        'comment_growth_rate': comment_growth_rate,
        'file_growth_rate': file_growth_rate,
        'popular_comments': [
            {
                'id': c.id,
                'author': c.author,
                'content': c.content[:50] + '...' if len(c.content) > 50 else c.content,
                'like_count': c.like_count,
                'created_at': c.created_at
            } for c in popular_comments
        ],
        'popular_files': [
            {
                'id': f.id,
                'name': f.name,
                'file_type': f.file_type,
                'download_count': f.download_count,
                'uploaded_at': f.uploaded_at
            } for f in popular_files
        ],
        'popular_search_terms': [
            {
                'query': term['properties__query'],
                'count': term['count']
            } for term in popular_search_terms if term['properties__query']
        ],
        'daily_activity': daily_activity,
        'top_users': top_users_data,
        'error_rate': round(error_rate, 2),
        'avg_response_time': 0.0,  # TODO: Implement response time tracking
        'uptime_percentage': 99.9  # TODO: Implement uptime tracking
    }
    
    serializer = AnalyticsDashboardSerializer(dashboard_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def real_time_stats(request):
    """
    Get real-time statistics
    """
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)
    ten_minutes_ago = now - timedelta(minutes=10)
    
    # Active users (users with activity in last 10 minutes)
    active_users_now = AnalyticsEvent.objects.filter(
        timestamp__gte=ten_minutes_ago,
        user__isnull=False
    ).values('user').distinct().count()
    
    # Last hour activity
    comments_last_hour = AnalyticsEvent.objects.filter(
        event_type='comment_post',
        timestamp__gte=one_hour_ago
    ).count()
    
    files_uploaded_last_hour = AnalyticsEvent.objects.filter(
        event_type='file_upload',
        timestamp__gte=one_hour_ago
    ).count()
    
    page_views_last_hour = AnalyticsEvent.objects.filter(
        event_type='page_view',
        timestamp__gte=one_hour_ago
    ).count()
    
    # Recent events
    recent_events = AnalyticsEvent.objects.filter(
        timestamp__gte=ten_minutes_ago
    ).exclude(
        event_type='page_view'  # Exclude page views to reduce noise
    ).order_by('-timestamp')[:10]
    
    recent_events_data = []
    for event in recent_events:
        recent_events_data.append({
            'event_name': event.event_name,
            'event_type': event.get_event_type_display(),
            'username': event.user.username if event.user else 'Anonymous',
            'timestamp': event.timestamp
        })
    
    # Trending pages (most viewed in last hour)
    trending_pages = AnalyticsEvent.objects.filter(
        event_type='page_view',
        timestamp__gte=one_hour_ago
    ).values('path').annotate(
        view_count=Count('id')
    ).order_by('-view_count')[:5]
    
    stats_data = {
        'active_users_now': active_users_now,
        'comments_last_hour': comments_last_hour,
        'files_uploaded_last_hour': files_uploaded_last_hour,
        'page_views_last_hour': page_views_last_hour,
        'recent_events': recent_events_data,
        'trending_pages': [
            {
                'path': page['path'],
                'view_count': page['view_count']
            } for page in trending_pages
        ],
        'visitor_countries': []  # TODO: Implement GeoIP lookup
    }
    
    serializer = RealTimeStatsSerializer(stats_data)
    return Response(serializer.data)


def calculate_growth_rate(current, previous):
    """
    Calculate growth rate percentage
    """
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def track_event(request):
    """
    Simple endpoint to track custom events
    """
    event_type = request.data.get('event_type', 'custom')
    event_name = request.data.get('event_name', 'Unknown Event')
    properties = request.data.get('properties', {})
    
    serializer = AnalyticsEventSerializer(
        data={
            'event_type': event_type,
            'event_name': event_name,
            'properties': properties
        },
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Event tracked successfully'
        }, status=status.HTTP_201_CREATED)
    
    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )
