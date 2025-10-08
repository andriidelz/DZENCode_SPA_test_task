from rest_framework import serializers
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import AnalyticsEvent, DailyStats, PopularContent, UserBehavior


class AnalyticsEventSerializer(serializers.ModelSerializer):
    """
    Serializer for AnalyticsEvent model
    """
    username = serializers.CharField(source='user.username', read_only=True)
    event_display = serializers.CharField(
        source='get_event_type_display',
        read_only=True
    )
    
    class Meta:
        model = AnalyticsEvent
        fields = [
            'id', 'event_type', 'event_display', 'event_name',
            'username', 'session_id', 'ip_address', 'path',
            'properties', 'timestamp', 'duration'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def create(self, validated_data):
        """Create analytics event with request metadata"""
        request = self.context.get('request')
        
        if request:
            if request.user.is_authenticated:
                validated_data['user'] = request.user
            
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            validated_data['referer'] = request.META.get('HTTP_REFERER', '')
            validated_data['path'] = request.path
            
            # Set session ID if available
            if hasattr(request, 'session'):
                validated_data['session_id'] = request.session.session_key or ''
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DailyStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for DailyStats model
    """
    total_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyStats
        fields = [
            'date', 'comments_count', 'comments_likes_count', 'comments_reports_count',
            'new_users_count', 'active_users_count', 'user_logins_count',
            'files_uploaded_count', 'files_downloaded_count', 'total_upload_size',
            'page_views_count', 'unique_visitors_count', 'searches_count',
            'errors_count', 'total_activity'
        ]
    
    def get_total_activity(self, obj):
        """Calculate total activity for the day"""
        return (
            obj.comments_count + obj.comments_likes_count +
            obj.user_logins_count + obj.files_uploaded_count +
            obj.files_downloaded_count + obj.searches_count
        )


class PopularContentSerializer(serializers.ModelSerializer):
    """
    Serializer for PopularContent model
    """
    content_type_display = serializers.CharField(
        source='get_content_type_display',
        read_only=True
    )
    popularity_score = serializers.SerializerMethodField()
    
    class Meta:
        model = PopularContent
        fields = [
            'id', 'content_type', 'content_type_display', 'content_id',
            'content_title', 'view_count', 'like_count', 'download_count',
            'views_today', 'views_this_week', 'views_this_month',
            'popularity_score', 'first_seen', 'last_updated'
        ]
    
    def get_popularity_score(self, obj):
        """Calculate popularity score based on various metrics"""
        score = (
            obj.view_count * 1 +
            obj.like_count * 3 +
            obj.download_count * 2 +
            obj.share_count * 5
        )
        
        # Boost recent content
        days_since_creation = (timezone.now() - obj.first_seen).days
        if days_since_creation < 7:
            score *= 1.5
        elif days_since_creation < 30:
            score *= 1.2
        
        return int(score)


class UserBehaviorSerializer(serializers.ModelSerializer):
    """
    Serializer for UserBehavior model
    """
    username = serializers.CharField(source='user.username', read_only=True)
    engagement_score = serializers.ReadOnlyField()
    avg_session_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = UserBehavior
        fields = [
            'username', 'total_sessions', 'avg_session_minutes',
            'comments_posted', 'comments_liked', 'files_uploaded',
            'files_downloaded', 'searches_performed', 'engagement_score',
            'preferred_content_types', 'most_active_hours', 'favorite_features',
            'first_activity', 'last_activity'
        ]
    
    def get_avg_session_minutes(self, obj):
        """Get average session duration in minutes"""
        if obj.avg_session_duration:
            return round(obj.avg_session_duration.total_seconds() / 60, 2)
        return 0


class AnalyticsDashboardSerializer(serializers.Serializer):
    """
    Serializer for analytics dashboard data
    """
    # Overview stats
    total_users = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    total_files = serializers.IntegerField()
    total_page_views = serializers.IntegerField()
    
    # Recent activity (last 30 days)
    recent_users = serializers.IntegerField()
    recent_comments = serializers.IntegerField()
    recent_files = serializers.IntegerField()
    recent_page_views = serializers.IntegerField()
    
    # Growth rates
    user_growth_rate = serializers.FloatField()
    comment_growth_rate = serializers.FloatField()
    file_growth_rate = serializers.FloatField()
    
    # Popular content
    popular_comments = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    popular_files = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    popular_search_terms = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    
    # Activity trends (last 7 days)
    daily_activity = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    
    # User engagement
    top_users = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    
    # System health
    error_rate = serializers.FloatField()
    avg_response_time = serializers.FloatField()
    uptime_percentage = serializers.FloatField()


class RealTimeStatsSerializer(serializers.Serializer):
    """
    Serializer for real-time statistics
    """
    # Current active users
    active_users_now = serializers.IntegerField()
    
    # Last hour activity
    comments_last_hour = serializers.IntegerField()
    files_uploaded_last_hour = serializers.IntegerField()
    page_views_last_hour = serializers.IntegerField()
    
    # Live events (last 10 minutes)
    recent_events = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    
    # Top pages right now
    trending_pages = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    
    # Geographic distribution
    visitor_countries = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
