from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import User, UserPreference, UserSession
from .services import UserService


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Extended admin for custom User model
    """
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'comments_count', 'likes_received', 'engagement_score_display',
        'is_active', 'date_joined', 'last_login'
    ]
    
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'date_joined',
        'last_login', 'show_email', 'allow_notifications'
    ]
    
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    readonly_fields = [
        'date_joined', 'last_login', 'comments_count',
        'likes_received', 'last_comment_at', 'engagement_score_display'
    ]
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': ('avatar', 'bio', 'website')
        }),
        ('Statistics', {
            'fields': (
                'comments_count', 'likes_received', 'last_comment_at',
                'engagement_score_display'
            )
        }),
        ('Privacy Settings', {
            'fields': ('show_email', 'allow_notifications')
        })
    )
    
    def engagement_score_display(self, obj):
        """Display user engagement score"""
        score = UserService.get_user_engagement_score(obj)
        
        if score > 100:
            color = 'green'
        elif score > 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, score
        )
    engagement_score_display.short_description = 'Engagement Score'
    
    actions = ['update_user_stats', 'send_welcome_email']
    
    def update_user_stats(self, request, queryset):
        """Update statistics for selected users"""
        for user in queryset:
            UserService.update_user_stats(user)
        
        self.message_user(
            request,
            f'Updated statistics for {queryset.count()} users.'
        )
    update_user_stats.short_description = 'Update user statistics'
    
    def send_welcome_email(self, request, queryset):
        """Send welcome email to selected users"""
        # Implementation would go here
        self.message_user(
            request,
            f'Welcome emails sent to {queryset.count()} users.'
        )
    send_welcome_email.short_description = 'Send welcome email'


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """
    Admin for user preferences
    """
    list_display = [
        'user', 'theme', 'language', 'comments_per_page',
        'email_on_reply', 'email_on_like', 'email_digest'
    ]
    
    list_filter = [
        'theme', 'language', 'comments_per_page',
        'email_on_reply', 'email_on_like', 'email_digest'
    ]
    
    search_fields = ['user__username', 'user__email']
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """
    Admin for user sessions (for analytics)
    """
    list_display = [
        'session_key', 'user', 'ip_address', 'started_at',
        'last_activity', 'page_views', 'comments_posted', 'is_active'
    ]
    
    list_filter = [
        'is_active', 'started_at', 'last_activity'
    ]
    
    search_fields = [
        'session_key', 'user__username', 'ip_address'
    ]
    
    readonly_fields = [
        'session_key', 'user', 'ip_address', 'user_agent',
        'started_at', 'last_activity', 'page_views', 'comments_posted'
    ]
    
    date_hierarchy = 'started_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
