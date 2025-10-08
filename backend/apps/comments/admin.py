from datetime import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Comment, CommentLike, CommentFile, CaptchaToken
from .services import SpamDetectionService


class CommentFileInline(admin.TabularInline):
    """
    Inline admin for comment files
    """
    model = CommentFile
    extra = 0
    readonly_fields = ('file_size', 'created_at')
    
    def has_add_permission(self, request, obj=None):
        return False


class CommentLikeInline(admin.TabularInline):
    """
    Inline admin for comment likes
    """
    model = CommentLike
    extra = 0
    readonly_fields = ('ip_address', 'created_at')
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Admin interface for comments with moderation capabilities
    """
    list_display = [
        'id', 'user_name', 'email_display', 'text_preview', 'parent_link',
        'created_at', 'likes_count', 'replies_count', 'is_active',
        'spam_score_display', 'moderation_status'
    ]
    
    list_filter = [
        'is_active', 'is_moderated', 'created_at', 'parent__isnull'
    ]
    
    search_fields = [
        'user_name', 'email', 'text', 'sanitized_text', 'ip_address'
    ]
    
    readonly_fields = [
        'sanitized_text', 'created_at', 'updated_at', 'ip_address',
        'user_agent', 'likes_count', 'replies_count', 'spam_score_display',
        'depth_display', 'thread_link'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_name', 'email', 'home_page')
        }),
        ('Content', {
            'fields': ('text', 'sanitized_text')
        }),
        ('Hierarchy', {
            'fields': ('parent', 'depth_display', 'thread_link')
        }),
        ('Metadata', {
            'fields': (
                'created_at', 'updated_at', 'ip_address', 'user_agent',
                'likes_count', 'replies_count'
            )
        }),
        ('Moderation', {
            'fields': (
                'is_active', 'is_moderated', 'moderated_by', 'moderated_at',
                'spam_score_display'
            )
        })
    )
    
    inlines = [CommentFileInline, CommentLikeInline]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    actions = [
        'mark_as_spam', 'mark_as_approved', 'bulk_moderate_spam'
    ]
    
    def email_display(self, obj):
        """Display email with privacy protection"""
        if obj.email:
            parts = obj.email.split('@')
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                masked_username = username[:2] + '*' * (len(username) - 2)
                return f"{masked_username}@{domain}"
        return obj.email
    email_display.short_description = 'Email'
    
    def text_preview(self, obj):
        """Display truncated text content"""
        preview = obj.text[:100]
        if len(obj.text) > 100:
            preview += '...'
        return preview
    text_preview.short_description = 'Text Preview'
    
    def parent_link(self, obj):
        """Display link to parent comment"""
        if obj.parent:
            url = reverse('admin:comments_comment_change', args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, f"#{obj.parent.id}")
        return '-'
    parent_link.short_description = 'Parent'
    
    def spam_score_display(self, obj):
        """Display spam score with color coding"""
        score = SpamDetectionService.get_spam_score(
            obj.text, obj.user_name, obj.email, obj.ip_address or '127.0.0.1'
        )
        
        if score > 80:
            color = 'red'
        elif score > 50:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, score
        )
    spam_score_display.short_description = 'Spam Score'
    
    def moderation_status(self, obj):
        """Display moderation status with colors"""
        if not obj.is_active:
            return format_html(
                '<span style="color: red; font-weight: bold;">Hidden</span>'
            )
        elif obj.is_moderated:
            return format_html(
                '<span style="color: green; font-weight: bold;">Approved</span>'
            )
        else:
            return format_html(
                '<span style="color: orange; font-weight: bold;">Pending</span>'
            )
    moderation_status.short_description = 'Status'
    
    def depth_display(self, obj):
        """Display comment nesting depth"""
        return obj.get_depth()
    depth_display.short_description = 'Depth'
    
    def thread_link(self, obj):
        """Display link to view full thread"""
        if obj.parent:
            root_comment = obj
            while root_comment.parent:
                root_comment = root_comment.parent
            
            url = reverse('admin:comments_comment_change', args=[root_comment.id])
            return format_html('<a href="{}">View Thread</a>', url)
        return 'Root Comment'
    thread_link.short_description = 'Thread'
    
    def mark_as_spam(self, request, queryset):
        """Mark selected comments as spam"""
        updated = queryset.update(
            is_active=False,
            is_moderated=True,
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} comments marked as spam.')
    mark_as_spam.short_description = 'Mark selected comments as spam'
    
    def mark_as_approved(self, request, queryset):
        """Mark selected comments as approved"""
        updated = queryset.update(
            is_active=True,
            is_moderated=True,
            moderated_by=request.user,
            moderated_at=timezone.now()
        )
        self.message_user(request, f'{updated} comments approved.')
    mark_as_approved.short_description = 'Mark selected comments as approved'
    
    def bulk_moderate_spam(self, request, queryset):
        """Automatically moderate based on spam score"""
        from django.utils import timezone
        
        moderated_count = 0
        for comment in queryset:
            score = SpamDetectionService.get_spam_score(
                comment.text, comment.user_name, comment.email, comment.ip_address or '127.0.0.1'
            )
            
            if score > 70:
                comment.is_active = False
                comment.is_moderated = True
                comment.moderated_by = request.user
                comment.moderated_at = timezone.now()
                comment.save()
                moderated_count += 1
        
        self.message_user(
            request,
            f'{moderated_count} comments automatically moderated based on spam score.'
        )
    bulk_moderate_spam.short_description = 'Auto-moderate based on spam score'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    """
    Admin interface for comment likes
    """
    list_display = ['id', 'comment_link', 'ip_address', 'created_at']
    list_filter = ['created_at']
    search_fields = ['comment__user_name', 'ip_address']
    readonly_fields = ['comment', 'ip_address', 'user_agent', 'created_at']
    
    def comment_link(self, obj):
        """Display link to the liked comment"""
        url = reverse('admin:comments_comment_change', args=[obj.comment.id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment.id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentFile)
class CommentFileAdmin(admin.ModelAdmin):
    """
    Admin interface for comment files
    """
    list_display = [
        'id', 'comment_link', 'file_type', 'original_name',
        'file_size_display', 'created_at'
    ]
    
    list_filter = ['file_type', 'created_at']
    search_fields = ['original_name', 'comment__user_name']
    readonly_fields = ['comment', 'file_size', 'created_at']
    
    def comment_link(self, obj):
        """Display link to the parent comment"""
        url = reverse('admin:comments_comment_change', args=[obj.comment.id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment.id}")
    comment_link.short_description = 'Comment'
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    file_size_display.short_description = 'File Size'


@admin.register(CaptchaToken)
class CaptchaTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for CAPTCHA tokens (mostly for debugging)
    """
    list_display = [
        'token', 'challenge', 'solution', 'ip_address',
        'created_at', 'used_at', 'is_expired_display'
    ]
    
    list_filter = ['created_at', 'used_at']
    search_fields = ['token', 'ip_address']
    readonly_fields = ['token', 'challenge', 'solution', 'created_at', 'used_at', 'ip_address']
    
    def is_expired_display(self, obj):
        """Display expiration status"""
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.is_used:
            return format_html('<span style="color: orange;">Used</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')
    is_expired_display.short_description = 'Status'
