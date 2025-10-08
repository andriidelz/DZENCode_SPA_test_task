from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from PIL import Image
import os


class UserProfile(models.Model):
    """
    Extended user profile model
    """
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='profile'
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Public display name"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="User biography"
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
        help_text="User avatar image"
    )
    website = models.URLField(
        blank=True,
        help_text="Personal website URL"
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="User location"
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth"
    )
    
    # Privacy settings
    is_email_public = models.BooleanField(
        default=False,
        help_text="Whether email is visible to other users"
    )
    is_profile_public = models.BooleanField(
        default=True,
        help_text="Whether profile is visible to other users"
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(
        default=True,
        help_text="Receive email notifications"
    )
    comment_notifications = models.BooleanField(
        default=True,
        help_text="Receive notifications for comment replies"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    last_active = models.DateTimeField(
        default=timezone.now
    )
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['last_active']),
        ]
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    @property
    def full_name(self):
        """Get user's full name or username"""
        if self.user.first_name and self.user.last_name:
            return f'{self.user.first_name} {self.user.last_name}'
        return self.user.username
    
    @property
    def public_name(self):
        """Get the name to display publicly"""
        return self.display_name or self.full_name
    
    @property
    def comment_count(self):
        """Get number of comments by this user"""
        return self.user.comments.filter(is_active=True).count()
    
    def save(self, *args, **kwargs):
        """
        Override save to handle avatar resizing
        """
        super().save(*args, **kwargs)
        
        if self.avatar:
            img = Image.open(self.avatar.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.avatar.path)


class UserActivity(models.Model):
    """
    Track user activity for analytics
    """
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('comment_post', 'Posted Comment'),
        ('comment_like', 'Liked Comment'),
        ('comment_report', 'Reported Comment'),
        ('profile_update', 'Updated Profile'),
    ]
    
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES
    )
    description = models.TextField(
        blank=True,
        help_text="Additional activity details"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        blank=True
    )
    timestamp = models.DateTimeField(
        auto_now_add=True
    )
    
    # Additional metadata as JSON
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata for the activity"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
        ]
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
    
    def __str__(self):
        return f'{self.user.username} - {self.get_activity_type_display()} at {self.timestamp}'


class UserSession(models.Model):
    """
    Track user sessions for security and analytics
    """
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_key = models.CharField(
        max_length=40,
        unique=True
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(
        blank=True
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Approximate location based on IP"
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    last_activity = models.DateTimeField(
        auto_now=True
    )
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['-last_activity']),
        ]
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
    
    def __str__(self):
        return f'{self.user.username} session from {self.ip_address}'
    
    @property
    def is_expired(self):
        """Check if session is expired"""
        return timezone.now() > self.expires_at
