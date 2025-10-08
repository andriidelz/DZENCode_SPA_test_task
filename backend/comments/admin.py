from django.contrib import admin
from .models import Comment, CommentLike, CommentReport


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Admin interface for Comment model
    """
    list_display = [
        'id', 'author', 'email', 'content_preview', 
        'likes_count', 'created_at', 'is_active'
    ]
    list_filter = [
        'is_active', 'created_at', 'updated_at'
    ]
    search_fields = [
        'author', 'email', 'content', 'ip_address'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'ip_address', 'user_agent'
    ]
    ordering = ['-created_at']
    list_per_page = 50
    
    fieldsets = (
        ('Comment Information', {
            'fields': ('author', 'email', 'content', 'is_active')
        }),
        ('Metadata', {
            'fields': ('user', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def content_preview(self, obj):
        """Show preview of comment content"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def likes_count(self, obj):
        """Show number of likes"""
        return obj.likes_count
    likes_count.short_description = 'Likes'
    
    actions = ['mark_active', 'mark_inactive']
    
    def mark_active(self, request, queryset):
        """Mark selected comments as active"""
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} comments marked as active.')
    mark_active.short_description = 'Mark selected comments as active'
    
    def mark_inactive(self, request, queryset):
        """Mark selected comments as inactive"""
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} comments marked as inactive.')
    mark_inactive.short_description = 'Mark selected comments as inactive'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    """
    Admin interface for CommentLike model
    """
    list_display = [
        'id', 'comment_preview', 'ip_address', 'created_at', 'is_active'
    ]
    list_filter = [
        'is_active', 'created_at'
    ]
    search_fields = [
        'comment__content', 'comment__author', 'ip_address'
    ]
    readonly_fields = [
        'id', 'created_at', 'ip_address', 'user_agent'
    ]
    ordering = ['-created_at']
    
    def comment_preview(self, obj):
        """Show preview of liked comment"""
        content = obj.comment.content
        return content[:30] + '...' if len(content) > 30 else content
    comment_preview.short_description = 'Comment'


@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    """
    Admin interface for CommentReport model
    """
    list_display = [
        'id', 'comment_preview', 'reason', 'reporter_email', 
        'created_at', 'is_resolved'
    ]
    list_filter = [
        'reason', 'is_resolved', 'created_at'
    ]
    search_fields = [
        'comment__content', 'comment__author', 'reporter_email', 'description'
    ]
    readonly_fields = [
        'id', 'created_at', 'ip_address'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('comment', 'reason', 'description', 'is_resolved')
        }),
        ('Reporter Details', {
            'fields': ('reporter_email', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def comment_preview(self, obj):
        """Show preview of reported comment"""
        content = obj.comment.content
        return content[:40] + '...' if len(content) > 40 else content
    comment_preview.short_description = 'Reported Comment'
    
    actions = ['mark_resolved', 'mark_unresolved']
    
    def mark_resolved(self, request, queryset):
        """Mark selected reports as resolved"""
        queryset.update(is_resolved=True)
        self.message_user(request, f'{queryset.count()} reports marked as resolved.')
    mark_resolved.short_description = 'Mark selected reports as resolved'
    
    def mark_unresolved(self, request, queryset):
        """Mark selected reports as unresolved"""
        queryset.update(is_resolved=False)
        self.message_user(request, f'{queryset.count()} reports marked as unresolved.')
    mark_unresolved.short_description = 'Mark selected reports as unresolved'
