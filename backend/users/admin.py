from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, UserActivity, UserSession


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for UserProfile
    """
    model = UserProfile
    can_delete = False
    verbose_name = 'Profile'
    verbose_name_plural = 'Profile'
    fields = [
        'display_name', 'bio', 'avatar', 'website', 'location',
        'is_email_public', 'is_profile_public',
        'email_notifications', 'comment_notifications'
    ]


class UserAdmin(BaseUserAdmin):
    """
    Extended User admin with profile inline
    """
    inlines = [UserProfileInline]
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'is_active', 'is_staff', 'date_joined', 'last_login'
    ]
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'date_joined'
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model
    """
    list_display = [
        'user', 'display_name', 'public_name', 'comment_count',
        'last_active', 'is_profile_public'
    ]
    list_filter = [
        'is_profile_public', 'is_email_public',
        'email_notifications', 'comment_notifications',
        'created_at', 'last_active'
    ]
    search_fields = [
        'user__username', 'user__email', 'display_name', 'bio'
    ]
    readonly_fields = [
        'user', 'created_at', 'updated_at', 'comment_count'
    ]
    ordering = ['-last_active']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'display_name', 'bio')
        }),
        ('Media', {
            'fields': ('avatar',),
        }),
        ('Contact Information', {
            'fields': ('website', 'location', 'birth_date'),
        }),
        ('Privacy Settings', {
            'fields': ('is_email_public', 'is_profile_public'),
        }),
        ('Notification Preferences', {
            'fields': ('email_notifications', 'comment_notifications'),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_active'),
            'classes': ('collapse',)
        })
    )
    
    def comment_count(self, obj):
        """Show number of comments"""
        return obj.comment_count
    comment_count.short_description = 'Comments'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    Admin interface for UserActivity model
    """
    list_display = [
        'user', 'activity_type', 'description', 'ip_address', 'timestamp'
    ]
    list_filter = [
        'activity_type', 'timestamp'
    ]
    search_fields = [
        'user__username', 'user__email', 'description', 'ip_address'
    ]
    readonly_fields = [
        'user', 'activity_type', 'description', 'ip_address',
        'user_agent', 'timestamp', 'metadata'
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """Disable adding activities manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable changing activities"""
        return False


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for UserSession model
    """
    list_display = [
        'user', 'ip_address', 'location', 'is_active',
        'created_at', 'last_activity', 'is_expired'
    ]
    list_filter = [
        'is_active', 'created_at', 'last_activity'
    ]
    search_fields = [
        'user__username', 'user__email', 'ip_address', 'location'
    ]
    readonly_fields = [
        'user', 'session_key', 'ip_address', 'user_agent',
        'created_at', 'last_activity', 'expires_at', 'is_expired'
    ]
    ordering = ['-last_activity']
    date_hierarchy = 'created_at'
    
    def is_expired(self, obj):
        """Show if session is expired"""
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
