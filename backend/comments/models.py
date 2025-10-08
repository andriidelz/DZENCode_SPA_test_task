from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.utils import timezone


class Comment(models.Model):
    """
    Model for storing user comments
    """
    author = models.CharField(
        max_length=100,
        help_text="Name of the comment author"
    )
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text="Email of the comment author"
    )
    content = models.TextField(
        help_text="Comment text content"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the comment was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the comment was last updated"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the comment is visible"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the comment author"
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User agent string of the comment author"
    )
    
    # For future user authentication integration
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comments',
        help_text="Associated user account if logged in"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
    
    def __str__(self):
        return f'Comment by {self.author} at {self.created_at}'
    
    @property
    def likes_count(self):
        """Get the number of likes for this comment"""
        return self.likes.filter(is_active=True).count()
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('comment-detail', kwargs={'pk': self.pk})


class CommentLike(models.Model):
    """
    Model for storing comment likes/reactions
    """
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the user who liked"
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User agent string"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    is_active = models.BooleanField(
        default=True
    )
    
    # For future user authentication integration
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comment_likes'
    )
    
    class Meta:
        # Prevent duplicate likes from same IP/user
        unique_together = [['comment', 'ip_address']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['comment', 'ip_address']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Comment Like'
        verbose_name_plural = 'Comment Likes'
    
    def __str__(self):
        return f'Like for comment {self.comment.id} from {self.ip_address}'


class CommentReport(models.Model):
    """
    Model for storing comment reports for moderation
    """
    REPORT_REASONS = [
        ('spam', 'Spam'),
        ('offensive', 'Offensive Content'),
        ('inappropriate', 'Inappropriate'),
        ('off_topic', 'Off Topic'),
        ('other', 'Other'),
    ]
    
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    reason = models.CharField(
        max_length=20,
        choices=REPORT_REASONS,
        default='other'
    )
    description = models.TextField(
        blank=True,
        help_text="Additional details about the report"
    )
    reporter_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email of the person reporting"
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the reporter"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether the report has been addressed"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['comment', 'is_resolved']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Comment Report'
        verbose_name_plural = 'Comment Reports'
    
    def __str__(self):
        return f'Report for comment {self.comment.id}: {self.reason}'
