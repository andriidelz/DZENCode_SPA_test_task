from django.contrib import admin
from .models import AnalyticsEvent, DailyStats, PopularContent, UserBehavior


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    """
    Admin interface for AnalyticsEvent model
    """
    list_display = [
        'id', 'event_name', 'event_type', 'user', 'ip_address', 'timestamp'
    ]
    list_filter = [
        'event_type', 'timestamp'
    ]
    search_fields = [
        'event_name', 'user__username', 'ip_address', 'path'
    ]
    readonly_fields = [
        'id', 'event_type', 'event_name', 'user', 'session_id',
        'ip_address', 'user_agent', 'referer', 'path',
        'properties', 'timestamp', 'duration'
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    list_per_page = 100
    
    def has_add_permission(self, request):
        """Disable adding events manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable changing events"""
        return False


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    """
    Admin interface for DailyStats model
    """
    list_display = [
        'date', 'comments_count', 'active_users_count', 'page_views_count',
        'files_uploaded_count', 'new_users_count', 'total_activity'
    ]
    list_filter = [
        'date'
    ]
    search_fields = [
        'date'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'total_activity'
    ]
    ordering = ['-date']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Comment Statistics', {
            'fields': ('comments_count', 'comments_likes_count', 'comments_reports_count')
        }),
        ('User Statistics', {
            'fields': ('new_users_count', 'active_users_count', 'user_logins_count')
        }),
        ('File Statistics', {
            'fields': ('files_uploaded_count', 'files_downloaded_count', 'total_upload_size')
        }),
        ('Page View Statistics', {
            'fields': ('page_views_count', 'unique_visitors_count')
        }),
        ('Other Statistics', {
            'fields': ('searches_count', 'errors_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_activity(self, obj):
        """Calculate total activity"""
        return (
            obj.comments_count + obj.comments_likes_count +
            obj.user_logins_count + obj.files_uploaded_count +
            obj.files_downloaded_count + obj.searches_count
        )
    total_activity.short_description = 'Total Activity'


@admin.register(PopularContent)
class PopularContentAdmin(admin.ModelAdmin):
    """
    Admin interface for PopularContent model
    """
    list_display = [
        'content_title', 'content_type', 'view_count', 'like_count',
        'views_today', 'views_this_week', 'last_updated'
    ]
    list_filter = [
        'content_type', 'last_updated'
    ]
    search_fields = [
        'content_title', 'content_id'
    ]
    readonly_fields = [
        'content_id', 'first_seen', 'last_updated'
    ]
    ordering = ['-view_count']
    
    fieldsets = (
        ('Content Information', {
            'fields': ('content_type', 'content_id', 'content_title')
        }),
        ('Popularity Metrics', {
            'fields': ('view_count', 'like_count', 'download_count', 'share_count')
        }),
        ('Time-based Metrics', {
            'fields': ('views_today', 'views_this_week', 'views_this_month')
        }),
        ('Timestamps', {
            'fields': ('first_seen', 'last_updated'),
            'classes': ('collapse',)
        })
    )


@admin.register(UserBehavior)
class UserBehaviorAdmin(admin.ModelAdmin):
    """
    Admin interface for UserBehavior model
    """
    list_display = [
        'user', 'engagement_score', 'total_sessions', 'comments_posted',
        'files_uploaded', 'last_activity'
    ]
    list_filter = [
        'last_activity', 'first_activity'
    ]
    search_fields = [
        'user__username', 'user__email'
    ]
    readonly_fields = [
        'user', 'first_activity', 'last_activity', 'last_updated', 'engagement_score'
    ]
    ordering = ['-engagement_score']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Activity Metrics', {
            'fields': ('total_sessions', 'total_time_spent', 'avg_session_duration')
        }),
        ('Engagement Metrics', {
            'fields': (
                'comments_posted', 'comments_liked', 'files_uploaded',
                'files_downloaded', 'searches_performed'
            )
        }),
        ('User Preferences', {
            'fields': ('preferred_content_types', 'most_active_hours', 'favorite_features'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('first_activity', 'last_activity', 'last_updated'),
            'classes': ('collapse',)
        })
    )
    
    def engagement_score(self, obj):
        """Show engagement score"""
        return obj.engagement_score
    engagement_score.short_description = 'Engagement Score'
