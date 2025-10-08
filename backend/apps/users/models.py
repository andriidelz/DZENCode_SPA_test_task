from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """
    Extended user model with additional fields
    """
    email = models.EmailField(unique=True)
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="User avatar image"
    )
    
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="User biography"
    )
    
    website = models.URLField(
        blank=True,
        help_text="User website URL"
    )
    
    # Statistics
    comments_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of comments"
    )
    
    likes_received = models.PositiveIntegerField(
        default=0,
        help_text="Total likes received on comments"
    )
    
    # Privacy settings
    show_email = models.BooleanField(
        default=False,
        help_text="Show email in public profile"
    )
    
    allow_notifications = models.BooleanField(
        default=True,
        help_text="Allow email notifications"
    )
    
    # Timestamps
    last_comment_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time user posted a comment"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.username


class UserSession(models.Model):
    """
    Track user sessions for analytics
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True
    )
    
    session_key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True
    )
    
    ip_address = models.GenericIPAddressField()
    
    user_agent = models.TextField(
        blank=True
    )
    
    started_at = models.DateTimeField(
        default=timezone.now
    )
    
    last_activity = models.DateTimeField(
        default=timezone.now
    )
    
    is_active = models.BooleanField(
        default=True
    )
    
    # Analytics data
    page_views = models.PositiveIntegerField(
        default=0
    )
    
    comments_posted = models.PositiveIntegerField(
        default=0
    )
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"Session {self.session_key} - {self.ip_address}"


class UserPreference(models.Model):
    """
    User preferences and settings
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    
    # Display preferences
    theme = models.CharField(
        max_length=20,
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto'),
        ],
        default='light'
    )
    
    language = models.CharField(
        max_length=10,
        choices=[
            ('en', 'English'),
            ('uk', 'Ukrainian'),
            ('ru', 'Russian'),
        ],
        default='en'
    )
    
    comments_per_page = models.PositiveIntegerField(
        default=25,
        choices=[
            (10, '10'),
            (25, '25'),
            (50, '50'),
            (100, '100'),
        ]
    )
    
    # Notification preferences
    email_on_reply = models.BooleanField(
        default=True,
        help_text="Send email when someone replies to your comment"
    )
    
    email_on_like = models.BooleanField(
        default=False,
        help_text="Send email when someone likes your comment"
    )
    
    email_digest = models.CharField(
        max_length=20,
        choices=[
            ('never', 'Never'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='weekly'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        db_table = 'user_preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
