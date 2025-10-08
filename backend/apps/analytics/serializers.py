from rest_framework import serializers
from .models import Event, DailyStats, UserActivity, PopularContent, SearchQuery


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for Event model
    """
    event_data_parsed = serializers.SerializerMethodField()
    content_object_str = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'event_type', 'user_identifier', 'ip_address',
            'created_at', 'event_data', 'event_data_parsed',
            'content_object_str', 'processed'
        ]
    
    def get_event_data_parsed(self, obj):
        """Get parsed event data"""
        return obj.get_event_data()
    
    def get_content_object_str(self, obj):
        """Get string representation of content object"""
        if obj.content_object:
            return str(obj.content_object)
        return None


class DailyStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for DailyStats model
    """
    total_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyStats
        fields = [
            'date', 'comments_created', 'comments_liked', 'replies_created',
            'files_uploaded', 'images_uploaded', 'text_files_uploaded',
            'new_users', 'user_logins', 'page_views', 'unique_visitors',
            'searches_performed', 'errors_occurred', 'total_activity',
            'created_at', 'updated_at'
        ]
    
    def get_total_activity(self, obj):
        """Calculate total activity score"""
        return (
            obj.comments_created + obj.comments_liked + obj.files_uploaded +
            obj.page_views + obj.searches_performed
        )


class UserActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for UserActivity model
    """
    session_duration_display = serializers.SerializerMethodField()
    total_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user_identifier', 'ip_address', 'session_id',
            'pages_visited', 'comments_posted', 'files_uploaded',
            'likes_given', 'searches_performed', 'session_start',
            'last_activity', 'session_duration', 'session_duration_display',
            'country', 'city', 'device_type', 'browser', 'os',
            'total_activity'
        ]
        read_only_fields = ['id', 'session_duration_display', 'total_activity']
    
    def get_session_duration_display(self, obj):
        """Get human-readable session duration"""
        duration = obj.session_duration
        if duration < 60:
            return f"{duration}s"
        elif duration < 3600:
            return f"{duration // 60}m {duration % 60}s"
        else:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def get_total_activity(self, obj):
        """Calculate total activity score"""
        return (
            obj.pages_visited + obj.comments_posted * 3 +
            obj.files_uploaded * 2 + obj.likes_given + obj.searches_performed
        )


class PopularContentSerializer(serializers.ModelSerializer):
    """
    Serializer for PopularContent model
    """
    content_url = serializers.SerializerMethodField()
    engagement_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = PopularContent
        fields = [
            'id', 'content_type', 'content_id', 'content_title',
            'view_count', 'like_count', 'share_count', 'comment_count',
            'popularity_score', 'date', 'content_url', 'engagement_rate'
        ]
    
    def get_content_url(self, obj):
        """Get URL to the content"""
        request = self.context.get('request')
        if not request:
            return None
        
        if obj.content_type == 'comment':
            return request.build_absolute_uri(f'/api/v1/comments/{obj.content_id}/')
        elif obj.content_type == 'file':
            return request.build_absolute_uri(f'/api/v1/files/{obj.content_id}/')
        
        return None
    
    def get_engagement_rate(self, obj):
        """Calculate engagement rate"""
        if obj.view_count > 0:
            engagement = (obj.like_count + obj.share_count + obj.comment_count)
            return round((engagement / obj.view_count) * 100, 2)
        return 0


class SearchQuerySerializer(serializers.ModelSerializer):
    """
    Serializer for SearchQuery model
    """
    response_time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'query', 'user_identifier', 'results_count',
            'response_time', 'response_time_display', 'clicked_result',
            'clicked_position', 'created_at'
        ]
    
    def get_response_time_display(self, obj):
        """Get human-readable response time"""
        if obj.response_time < 1000:
            return f"{obj.response_time:.0f}ms"
        else:
            return f"{obj.response_time / 1000:.2f}s"


class AnalyticsDashboardSerializer(serializers.Serializer):
    """
    Serializer for analytics dashboard data
    """
    totals = serializers.DictField()
    trend_data = serializers.ListField()
    top_searches = serializers.ListField()
    active_users = serializers.IntegerField()
    avg_session_duration = serializers.FloatField()
    popular_comments = PopularContentSerializer(many=True)
    popular_files = PopularContentSerializer(many=True)


class AnalyticsStatsSerializer(serializers.Serializer):
    """
    Serializer for general analytics statistics
    """
    total_events = serializers.IntegerField()
    events_today = serializers.IntegerField()
    active_users_today = serializers.IntegerField()
    top_event_types = serializers.ListField()
    avg_events_per_day = serializers.FloatField()
    growth_rate = serializers.FloatField()


class UserEngagementSerializer(serializers.Serializer):
    """
    Serializer for user engagement metrics
    """
    user_identifier = serializers.CharField()
    total_sessions = serializers.IntegerField()
    total_session_time = serializers.IntegerField()
    avg_session_time = serializers.FloatField()
    total_page_views = serializers.IntegerField()
    engagement_score = serializers.FloatField()
    last_activity = serializers.DateTimeField()


class RealtimeStatsSerializer(serializers.Serializer):
    """
    Serializer for real-time statistics
    """
    stats = serializers.DictField()
    active_users = serializers.IntegerField()
    period_minutes = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
