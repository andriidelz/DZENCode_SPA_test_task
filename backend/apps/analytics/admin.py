from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Event, DailyStats, UserActivity, PopularContent, SearchQuery
from .services import AnalyticsService


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    Admin interface for events
    """
    list_display = [
        'id', 'event_type', 'user_identifier', 'content_object_link',
        'ip_address', 'created_at', 'processed_status'
    ]
    
    list_filter = [
        'event_type', 'processed', 'created_at', 'content_type'
    ]
    
    search_fields = [
        'user_identifier', 'ip_address', 'event_data'
    ]
    
    readonly_fields = [
        'content_type', 'object_id', 'content_object', 'event_data',
        'ip_address', 'user_agent', 'referer', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    actions = ['mark_as_processed', 'mark_as_unprocessed']
    
    def content_object_link(self, obj):
        """Display link to content object"""
        if obj.content_object:
            return format_html(
                '<a href="{}">{}</a>',
                f'/admin/{obj.content_type.app_label}/{obj.content_type.model}/{obj.object_id}/',
                str(obj.content_object)[:50]
            )
        return '-'
    content_object_link.short_description = 'Content Object'
    
    def processed_status(self, obj):
        """Display processing status with colors"""
        if obj.processed:
            return format_html('<span style="color: green;">✓ Processed</span>')
        else:
            return format_html('<span style="color: red;">✗ Pending</span>')
    processed_status.short_description = 'Status'
    
    def mark_as_processed(self, request, queryset):
        """Mark selected events as processed"""
        updated = queryset.update(processed=True)
        self.message_user(request, f'{updated} events marked as processed.')
    mark_as_processed.short_description = 'Mark as processed'
    
    def mark_as_unprocessed(self, request, queryset):
        """Mark selected events as unprocessed"""
        updated = queryset.update(processed=False)
        self.message_user(request, f'{updated} events marked as unprocessed.')
    mark_as_unprocessed.short_description = 'Mark as unprocessed'


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    """
    Admin interface for daily statistics
    """
    list_display = [
        'date', 'comments_created', 'comments_liked', 'files_uploaded',
        'new_users', 'page_views', 'unique_visitors', 'total_activity',
        'updated_at'
    ]
    
    list_filter = ['date']
    
    search_fields = ['date']
    
    readonly_fields = ['created_at', 'updated_at', 'total_activity']
    
    date_hierarchy = 'date'
    ordering = ['-date']
    
    actions = ['recalculate_stats']
    
    def total_activity(self, obj):
        """Calculate total activity score"""
        return (
            obj.comments_created + obj.comments_liked + obj.files_uploaded +
            obj.page_views + obj.searches_performed
        )
    total_activity.short_description = 'Total Activity'
    
    def recalculate_stats(self, request, queryset):
        """Recalculate statistics for selected dates"""
        updated_count = 0
        for stats in queryset:
            AnalyticsService.update_daily_stats(stats.date)
            updated_count += 1
        
        self.message_user(
            request,
            f'Recalculated statistics for {updated_count} dates.'
        )
    recalculate_stats.short_description = 'Recalculate statistics'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    Admin interface for user activity
    """
    list_display = [
        'id', 'user_identifier', 'ip_address', 'session_start',
        'session_duration_display', 'pages_visited', 'comments_posted',
        'total_activity_score', 'device_type', 'browser'
    ]
    
    list_filter = [
        'session_start', 'device_type', 'browser', 'country'
    ]
    
    search_fields = [
        'user_identifier', 'ip_address', 'session_id'
    ]
    
    readonly_fields = [
        'session_id', 'ip_address', 'user_agent', 'session_start',
        'last_activity', 'session_duration', 'session_duration_display'
    ]
    
    date_hierarchy = 'session_start'
    ordering = ['-session_start']
    
    def session_duration_display(self, obj):
        """Display session duration in human readable format"""
        duration = obj.session_duration
        if duration < 60:
            return f"{duration}s"
        elif duration < 3600:
            return f"{duration // 60}m {duration % 60}s"
        else:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            return f"{hours}h {minutes}m"
    session_duration_display.short_description = 'Duration'
    
    def total_activity_score(self, obj):
        """Calculate total activity score"""
        return (
            obj.pages_visited + obj.comments_posted * 3 +
            obj.files_uploaded * 2 + obj.likes_given + obj.searches_performed
        )
    total_activity_score.short_description = 'Activity Score'


@admin.register(PopularContent)
class PopularContentAdmin(admin.ModelAdmin):
    """
    Admin interface for popular content
    """
    list_display = [
        'id', 'content_type', 'content_id', 'content_title_short',
        'popularity_score', 'view_count', 'like_count', 'comment_count',
        'date', 'engagement_rate'
    ]
    
    list_filter = [
        'content_type', 'date'
    ]
    
    search_fields = [
        'content_title', 'content_id'
    ]
    
    readonly_fields = [
        'content_type', 'content_id', 'popularity_score',
        'created_at', 'updated_at', 'engagement_rate'
    ]
    
    date_hierarchy = 'date'
    ordering = ['-popularity_score', '-date']
    
    actions = ['recalculate_popularity']
    
    def content_title_short(self, obj):
        """Display truncated content title"""
        return obj.content_title[:50] + '...' if len(obj.content_title) > 50 else obj.content_title
    content_title_short.short_description = 'Title'
    
    def engagement_rate(self, obj):
        """Calculate engagement rate"""
        if obj.view_count > 0:
            engagement = (obj.like_count + obj.share_count + obj.comment_count)
            rate = (engagement / obj.view_count) * 100
            return f"{rate:.1f}%"
        return "0%"
    engagement_rate.short_description = 'Engagement Rate'
    
    def recalculate_popularity(self, request, queryset):
        """Recalculate popularity scores"""
        updated_count = 0
        for content in queryset:
            content.calculate_popularity_score()
            content.save()
            updated_count += 1
        
        self.message_user(
            request,
            f'Recalculated popularity for {updated_count} items.'
        )
    recalculate_popularity.short_description = 'Recalculate popularity'


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    """
    Admin interface for search queries
    """
    list_display = [
        'id', 'query', 'user_identifier', 'results_count',
        'response_time_display', 'clicked_result', 'clicked_position',
        'created_at'
    ]
    
    list_filter = [
        'clicked_result', 'created_at', 'results_count'
    ]
    
    search_fields = [
        'query', 'user_identifier', 'ip_address'
    ]
    
    readonly_fields = [
        'query', 'user_identifier', 'ip_address', 'results_count',
        'response_time', 'clicked_result', 'clicked_position', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def response_time_display(self, obj):
        """Display response time in human readable format"""
        if obj.response_time < 1000:
            return f"{obj.response_time:.0f}ms"
        else:
            return f"{obj.response_time / 1000:.2f}s"
    response_time_display.short_description = 'Response Time'


# Custom admin views for analytics dashboard
class AnalyticsAdminMixin:
    """
    Mixin to add analytics context to admin views
    """
    
    def changelist_view(self, request, extra_context=None):
        # Add analytics data to context
        response = super().changelist_view(request, extra_context=extra_context)
        
        if hasattr(response, 'context_data'):
            # Get recent statistics
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            
            stats = {
                'events_today': Event.objects.filter(
                    created_at__date=today
                ).count(),
                'events_this_week': Event.objects.filter(
                    created_at__date__gte=week_ago
                ).count(),
                'active_users_today': UserActivity.objects.filter(
                    last_activity__date=today
                ).values('user_identifier').distinct().count(),
                'top_event_types': Event.objects.filter(
                    created_at__date__gte=week_ago
                ).values('event_type').annotate(
                    count=Count('id')
                ).order_by('-count')[:5]
            }
            
            response.context_data['analytics_stats'] = stats
        
        return response


# Apply mixin to main admin classes
class AnalyticsEventAdmin(AnalyticsAdminMixin, EventAdmin):
    pass


# Register the enhanced admin
admin.site.unregister(Event)
admin.site.register(Event, AnalyticsEventAdmin)


# Add custom admin actions
def cleanup_old_analytics_data(modeladmin, request, queryset):
    """
    Custom admin action to cleanup old analytics data
    """
    from .tasks import cleanup_old_analytics_data
    
    # Trigger async cleanup
    cleanup_old_analytics_data.delay()
    
    modeladmin.message_user(
        request,
        "Analytics cleanup task has been queued."
    )

cleanup_old_analytics_data.short_description = "Cleanup old analytics data"


def update_popular_content(modeladmin, request, queryset):
    """
    Custom admin action to update popular content
    """
    from .tasks import update_popular_content
    
    # Trigger async update
    update_popular_content.delay()
    
    modeladmin.message_user(
        request,
        "Popular content update task has been queued."
    )

update_popular_content.short_description = "Update popular content rankings"


# Add actions to admin site
admin.site.add_action(cleanup_old_analytics_data)
admin.site.add_action(update_popular_content)
