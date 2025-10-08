from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from django.db.models import Count, Sum, Avg
from datetime import timedelta
from django.utils import timezone

from .models import Event, DailyStats, UserActivity, PopularContent, SearchQuery
from .services import AnalyticsService, RealtimeAnalyticsService
from .serializers import (
    EventSerializer,
    DailyStatsSerializer,
    UserActivitySerializer,
    PopularContentSerializer,
    SearchQuerySerializer,
    AnalyticsDashboardSerializer
)


@extend_schema(
    summary="Get analytics dashboard",
    description="Get comprehensive analytics data for the dashboard"
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
@cache_page(60 * 15)  # Cache for 15 minutes
def analytics_dashboard(request):
    """
    Get analytics dashboard data
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
        if days not in [7, 30, 90]:
            days = 30
    except (ValueError, TypeError):
        days = 30
    
    data = AnalyticsService.get_analytics_dashboard_data(days)
    serializer = AnalyticsDashboardSerializer(data)
    
    return Response(serializer.data)


@extend_schema(
    summary="Get real-time analytics",
    description="Get real-time analytics data"
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def realtime_analytics(request):
    """
    Get real-time analytics data
    """
    minutes = request.GET.get('minutes', 30)
    try:
        minutes = int(minutes)
        if minutes > 60:
            minutes = 60
    except (ValueError, TypeError):
        minutes = 30
    
    try:
        realtime_service = RealtimeAnalyticsService()
        
        stats = realtime_service.get_realtime_stats(minutes)
        active_users = realtime_service.get_active_users_count(15)
        
        return Response({
            'stats': stats,
            'active_users': active_users,
            'period_minutes': minutes
        })
    
    except Exception as e:
        return Response(
            {'error': f'Real-time analytics unavailable: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@extend_schema(
    summary="Get search analytics",
    description="Get search analytics and trends"
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
@cache_page(60 * 30)  # Cache for 30 minutes
def search_analytics(request):
    """
    Get search analytics data
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
        if days > 365:
            days = 365
    except (ValueError, TypeError):
        days = 30
    
    data = AnalyticsService.get_search_analytics(days)
    
    return Response(data)


class DailyStatsListView(generics.ListAPIView):
    """
    List daily statistics
    """
    serializer_class = DailyStatsSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        days = self.request.GET.get('days', 30)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 30
        
        start_date = timezone.now().date() - timedelta(days=days)
        return DailyStats.objects.filter(date__gte=start_date).order_by('-date')
    
    @method_decorator(cache_page(60 * 30))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="List daily statistics",
        description="Get daily statistics for a specified period"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EventListView(generics.ListAPIView):
    """
    List recent events
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = Event.objects.all().order_by('-created_at')
        
        # Filter by event type
        event_type = self.request.GET.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by user
        user_identifier = self.request.GET.get('user')
        if user_identifier:
            queryset = queryset.filter(user_identifier=user_identifier)
        
        # Filter by date range
        hours = self.request.GET.get('hours', 24)
        try:
            hours = int(hours)
        except (ValueError, TypeError):
            hours = 24
        
        start_time = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(created_at__gte=start_time)
        
        return queryset[:100]  # Limit to 100 recent events
    
    @extend_schema(
        summary="List recent events",
        description="Get recent system events with filtering options"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserActivityListView(generics.ListAPIView):
    """
    List user activity sessions
    """
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = UserActivity.objects.all().order_by('-session_start')
        
        # Filter by user
        user_identifier = self.request.GET.get('user')
        if user_identifier:
            queryset = queryset.filter(user_identifier=user_identifier)
        
        # Filter by date range
        days = self.request.GET.get('days', 7)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 7
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(session_start__gte=start_date)
        
        return queryset[:50]  # Limit to 50 sessions
    
    @method_decorator(cache_page(60 * 10))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="List user activity",
        description="Get user activity sessions with filtering options"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PopularContentListView(generics.ListAPIView):
    """
    List popular content
    """
    serializer_class = PopularContentSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        content_type = self.request.GET.get('type', 'comment')
        days = self.request.GET.get('days', 7)
        
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 7
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        return PopularContent.objects.filter(
            content_type=content_type,
            date__gte=start_date
        ).order_by('-popularity_score')[:20]
    
    @method_decorator(cache_page(60 * 30))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="List popular content",
        description="Get popular content ranked by engagement"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(
    summary="Get user statistics",
    description="Get statistics for a specific user"
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def user_statistics(request, user_identifier):
    """
    Get statistics for a specific user
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 30
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Get user events
    events = Event.objects.filter(
        user_identifier=user_identifier,
        created_at__gte=start_date
    )
    
    # Aggregate event counts
    event_counts = events.values('event_type').annotate(count=Count('id'))
    
    # Get user activity
    activities = UserActivity.objects.filter(
        user_identifier=user_identifier,
        session_start__gte=start_date
    )
    
    # Calculate statistics
    total_sessions = activities.count()
    total_session_time = activities.aggregate(
        total=Sum('session_duration')
    )['total'] or 0
    
    avg_session_time = activities.aggregate(
        avg=Avg('session_duration')
    )['avg'] or 0
    
    total_page_views = activities.aggregate(
        total=Sum('pages_visited')
    )['total'] or 0
    
    return Response({
        'user_identifier': user_identifier,
        'period_days': days,
        'event_counts': {item['event_type']: item['count'] for item in event_counts},
        'total_sessions': total_sessions,
        'total_session_time': total_session_time,
        'avg_session_time': avg_session_time,
        'total_page_views': total_page_views,
        'recent_activity': UserActivitySerializer(
            activities.order_by('-session_start')[:5], many=True
        ).data
    })


@extend_schema(
    summary="Get system health metrics",
    description="Get system health and performance metrics"
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def system_health(request):
    """
    Get system health metrics
    """
    hours = request.GET.get('hours', 24)
    try:
        hours = int(hours)
    except (ValueError, TypeError):
        hours = 24
    
    start_time = timezone.now() - timedelta(hours=hours)
    
    # Get error events
    error_events = Event.objects.filter(
        event_type='error_occurred',
        created_at__gte=start_time
    ).count()
    
    # Get recent activity
    recent_events = Event.objects.filter(
        created_at__gte=start_time
    ).count()
    
    # Get active users
    active_users = UserActivity.objects.filter(
        last_activity__gte=timezone.now() - timedelta(minutes=15)
    ).count()
    
    # Get average response times from search queries
    avg_search_time = SearchQuery.objects.filter(
        created_at__gte=start_time
    ).aggregate(avg=Avg('response_time'))['avg'] or 0
    
    # Calculate health score (simple algorithm)
    health_score = 100
    
    if error_events > 10:
        health_score -= min(20, error_events)
    
    if avg_search_time > 1000:  # If search takes more than 1 second
        health_score -= 10
    
    if recent_events == 0:
        health_score -= 30  # No activity might indicate issues
    
    health_score = max(0, health_score)
    
    return Response({
        'health_score': health_score,
        'period_hours': hours,
        'error_events': error_events,
        'total_events': recent_events,
        'active_users': active_users,
        'avg_search_response_time': avg_search_time,
        'status': 'healthy' if health_score > 80 else 'warning' if health_score > 50 else 'critical'
    })


@extend_schema(
    summary="Export analytics data",
    description="Export analytics data in CSV format"
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def export_analytics(request):
    """
    Export analytics data as CSV
    """
    export_type = request.GET.get('type', 'daily_stats')
    days = request.GET.get('days', 30)
    
    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 30
    
    start_date = timezone.now().date() - timedelta(days=days)
    
    from django.http import HttpResponse
    import csv
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{export_type}_{start_date}_to_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    
    if export_type == 'daily_stats':
        writer.writerow([
            'Date', 'Comments Created', 'Comments Liked', 'Replies Created',
            'Files Uploaded', 'New Users', 'Page Views', 'Unique Visitors',
            'Searches Performed', 'Errors Occurred'
        ])
        
        stats = DailyStats.objects.filter(date__gte=start_date).order_by('date')
        for stat in stats:
            writer.writerow([
                stat.date, stat.comments_created, stat.comments_liked,
                stat.replies_created, stat.files_uploaded, stat.new_users,
                stat.page_views, stat.unique_visitors, stat.searches_performed,
                stat.errors_occurred
            ])
    
    elif export_type == 'search_queries':
        writer.writerow([
            'Query', 'Results Count', 'Response Time', 'User', 'IP Address', 'Created At'
        ])
        
        start_datetime = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
        
        queries = SearchQuery.objects.filter(
            created_at__gte=start_datetime
        ).order_by('-created_at')[:1000]  # Limit to 1000 queries
        
        for query in queries:
            writer.writerow([
                query.query, query.results_count, query.response_time,
                query.user_identifier, query.ip_address, query.created_at
            ])
    
    else:
        return Response(
            {'error': 'Invalid export type'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return response
