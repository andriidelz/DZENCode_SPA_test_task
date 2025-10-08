from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import JSONField
from datetime import timedelta


class AnalyticsEvent(models.Model):
    """
    Model for tracking analytics events
    """
    EVENT_TYPES = [
        ('page_view', 'Page View'),
        ('comment_post', 'Comment Posted'),
        ('comment_like', 'Comment Liked'),
        ('comment_report', 'Comment Reported'),
        ('file_upload', 'File Uploaded'),
        ('file_download', 'File Downloaded'),
        ('user_register', 'User Registered'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('search', 'Search Performed'),
        ('error', 'Error Occurred'),
        ('custom', 'Custom Event'),
    ]
    
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        db_index=True
    )
    event_name = models.CharField(
        max_length=100,
        help_text="Specific event name"
    )
    
    # User information
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events'
    )
    session_id = models.CharField(
        max_length=40,
        blank=True,
        help_text="Session identifier"
    )
    
    # Request information
    ip_address = models.GenericIPAddressField(
        db_index=True
    )
    user_agent = models.TextField(
        blank=True
    )
    referer = models.URLField(
        blank=True,
        max_length=500
    )
    path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Request path"
    )
    
    # Event metadata
    properties = JSONField(
        default=dict,
        blank=True,
        help_text="Additional event properties as JSON"
    )
    
    # Timing
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Event duration (if applicable)"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        verbose_name = 'Analytics Event'
        verbose_name_plural = 'Analytics Events'
    
    def __str__(self):
        return f'{self.event_name} at {self.timestamp}'


class DailyStats(models.Model):
    """
    Model for storing daily aggregated statistics
    """
    date = models.DateField(
        unique=True,
        db_index=True
    )
    
    # Comment stats
    comments_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of comments posted"
    )
    comments_likes_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of comment likes"
    )
    comments_reports_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of comment reports"
    )
    
    # User stats
    new_users_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of new user registrations"
    )
    active_users_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of active users"
    )
    user_logins_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of user logins"
    )
    
    # File stats
    files_uploaded_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of files uploaded"
    )
    files_downloaded_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of file downloads"
    )
    total_upload_size = models.BigIntegerField(
        default=0,
        help_text="Total size of uploaded files in bytes"
    )
    
    # Page view stats
    page_views_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of page views"
    )
    unique_visitors_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of unique visitors (by IP)"
    )
    
    # Search stats
    searches_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of searches performed"
    )
    
    # Error stats
    errors_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of errors occurred"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Daily Stats'
        verbose_name_plural = 'Daily Stats'
    
    def __str__(self):
        return f'Stats for {self.date}'


class PopularContent(models.Model):
    """
    Model for tracking popular content
    """
    CONTENT_TYPES = [
        ('comment', 'Comment'),
        ('file', 'File'),
        ('search_term', 'Search Term'),
        ('page', 'Page'),
    ]
    
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPES,
        db_index=True
    )
    content_id = models.CharField(
        max_length=100,
        help_text="ID or identifier of the content"
    )
    content_title = models.CharField(
        max_length=255,
        help_text="Title or name of the content"
    )
    
    # Popularity metrics
    view_count = models.PositiveIntegerField(
        default=0
    )
    like_count = models.PositiveIntegerField(
        default=0
    )
    download_count = models.PositiveIntegerField(
        default=0
    )
    share_count = models.PositiveIntegerField(
        default=0
    )
    
    # Time-based metrics
    views_today = models.PositiveIntegerField(
        default=0
    )
    views_this_week = models.PositiveIntegerField(
        default=0
    )
    views_this_month = models.PositiveIntegerField(
        default=0
    )
    
    # Metadata
    first_seen = models.DateTimeField(
        auto_now_add=True
    )
    last_updated = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        unique_together = ['content_type', 'content_id']
        ordering = ['-view_count']
        indexes = [
            models.Index(fields=['content_type', '-view_count']),
            models.Index(fields=['-views_today']),
            models.Index(fields=['-views_this_week']),
        ]
        verbose_name = 'Popular Content'
        verbose_name_plural = 'Popular Content'
    
    def __str__(self):
        return f'{self.content_title} ({self.content_type}) - {self.view_count} views'


class UserBehavior(models.Model):
    """
    Model for tracking user behavior patterns
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='behavior_data'
    )
    
    # Activity metrics
    total_sessions = models.PositiveIntegerField(
        default=0
    )
    total_time_spent = models.DurationField(
        default=timedelta(0),
        help_text="Total time spent on the platform"
    )
    avg_session_duration = models.DurationField(
        default=timedelta(0)
    )
    
    # Engagement metrics
    comments_posted = models.PositiveIntegerField(
        default=0
    )
    comments_liked = models.PositiveIntegerField(
        default=0
    )
    files_uploaded = models.PositiveIntegerField(
        default=0
    )
    files_downloaded = models.PositiveIntegerField(
        default=0
    )
    searches_performed = models.PositiveIntegerField(
        default=0
    )
    
    # User preferences (inferred)
    preferred_content_types = JSONField(
        default=dict,
        help_text="Preferred content types based on activity"
    )
    most_active_hours = JSONField(
        default=list,
        help_text="Hours when user is most active"
    )
    favorite_features = JSONField(
        default=list,
        help_text="Most used features"
    )
    
    # Timestamps
    first_activity = models.DateTimeField(
        null=True,
        blank=True
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True
    )
    last_updated = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'User Behavior'
        verbose_name_plural = 'User Behaviors'
    
    def __str__(self):
        return f'Behavior data for {self.user.username}'
    
    @property
    def engagement_score(self):
        """
        Calculate user engagement score (0-100)
        """
        score = 0
        
        # Comments factor (max 30 points)
        score += min(self.comments_posted * 2, 30)
        
        # Likes factor (max 20 points)
        score += min(self.comments_liked, 20)
        
        # Files factor (max 25 points)
        score += min((self.files_uploaded * 3) + self.files_downloaded, 25)
        
        # Activity factor (max 25 points)
        if self.total_sessions > 0:
            avg_duration_minutes = self.avg_session_duration.total_seconds() / 60
            score += min(avg_duration_minutes / 2, 25)
        
        return min(int(score), 100)
