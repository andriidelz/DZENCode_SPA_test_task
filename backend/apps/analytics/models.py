from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json


class Event(models.Model):
    """
    Base model for tracking events in the system
    """
    EVENT_TYPES = (
        ('comment_created', 'Comment Created'),
        ('comment_liked', 'Comment Liked'),
        ('comment_replied', 'Comment Replied'),
        ('file_uploaded', 'File Uploaded'),
        ('user_registered', 'User Registered'),
        ('user_login', 'User Login'),
        ('page_view', 'Page View'),
        ('search_performed', 'Search Performed'),
        ('error_occurred', 'Error Occurred'),
    )
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        db_index=True,
        help_text="Type of event"
    )
    
    # Generic foreign key to link to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # User information (for anonymous users)
    user_identifier = models.CharField(
        max_length=255,
        blank=True,
        help_text="Username or session identifier"
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of the user"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    referer = models.URLField(
        blank=True,
        help_text="HTTP referer"
    )
    
    # Event data (JSON)
    event_data = models.TextField(
        blank=True,
        help_text="Additional event data as JSON"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    # Processing status
    processed = models.BooleanField(
        default=False,
        help_text="Whether this event has been processed for analytics"
    )
    
    class Meta:
        db_table = 'analytics_events'
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['user_identifier', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['processed', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.created_at}"
    
    def get_event_data(self):
        """Parse event data JSON"""
        if self.event_data:
            try:
                return json.loads(self.event_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_event_data(self, data):
        """Set event data as JSON"""
        self.event_data = json.dumps(data, default=str)


class DailyStats(models.Model):
    """
    Daily aggregated statistics
    """
    date = models.DateField(
        unique=True,
        db_index=True,
        help_text="Date for these statistics"
    )
    
    # Comment statistics
    comments_created = models.PositiveIntegerField(
        default=0,
        help_text="Number of comments created"
    )
    
    comments_liked = models.PositiveIntegerField(
        default=0,
        help_text="Number of likes given"
    )
    
    replies_created = models.PositiveIntegerField(
        default=0,
        help_text="Number of replies created"
    )
    
    # File statistics
    files_uploaded = models.PositiveIntegerField(
        default=0,
        help_text="Number of files uploaded"
    )
    
    images_uploaded = models.PositiveIntegerField(
        default=0,
        help_text="Number of images uploaded"
    )
    
    text_files_uploaded = models.PositiveIntegerField(
        default=0,
        help_text="Number of text files uploaded"
    )
    
    # User statistics
    new_users = models.PositiveIntegerField(
        default=0,
        help_text="Number of new user registrations"
    )
    
    user_logins = models.PositiveIntegerField(
        default=0,
        help_text="Number of user logins"
    )
    
    # Traffic statistics
    page_views = models.PositiveIntegerField(
        default=0,
        help_text="Number of page views"
    )
    
    unique_visitors = models.PositiveIntegerField(
        default=0,
        help_text="Number of unique visitors (by IP)"
    )
    
    # Search statistics
    searches_performed = models.PositiveIntegerField(
        default=0,
        help_text="Number of searches performed"
    )
    
    # Error statistics
    errors_occurred = models.PositiveIntegerField(
        default=0,
        help_text="Number of errors occurred"
    )
    
    # Processing metadata
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        db_table = 'analytics_daily_stats'
        ordering = ['-date']
    
    def __str__(self):
        return f"Stats for {self.date}"


class UserActivity(models.Model):
    """
    Track user activity sessions
    """
    # User identification
    user_identifier = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Username, email, or session ID"
    )
    
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the user"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    # Session information
    session_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Session identifier"
    )
    
    # Activity data
    pages_visited = models.PositiveIntegerField(
        default=0,
        help_text="Number of pages visited in this session"
    )
    
    comments_posted = models.PositiveIntegerField(
        default=0,
        help_text="Number of comments posted in this session"
    )
    
    files_uploaded = models.PositiveIntegerField(
        default=0,
        help_text="Number of files uploaded in this session"
    )
    
    likes_given = models.PositiveIntegerField(
        default=0,
        help_text="Number of likes given in this session"
    )
    
    searches_performed = models.PositiveIntegerField(
        default=0,
        help_text="Number of searches performed in this session"
    )
    
    # Time tracking
    session_start = models.DateTimeField(
        default=timezone.now,
        help_text="When the session started"
    )
    
    last_activity = models.DateTimeField(
        default=timezone.now,
        help_text="Last activity timestamp"
    )
    
    session_duration = models.PositiveIntegerField(
        default=0,
        help_text="Session duration in seconds"
    )
    
    # Geographic data (if available)
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country of the user"
    )
    
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City of the user"
    )
    
    # Device information
    device_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Device type (mobile, desktop, tablet)"
    )
    
    browser = models.CharField(
        max_length=100,
        blank=True,
        help_text="Browser name and version"
    )
    
    os = models.CharField(
        max_length=100,
        blank=True,
        help_text="Operating system"
    )
    
    class Meta:
        db_table = 'analytics_user_activity'
        indexes = [
            models.Index(fields=['user_identifier', 'session_start']),
            models.Index(fields=['ip_address', 'session_start']),
            models.Index(fields=['session_start']),
            models.Index(fields=['last_activity']),
        ]
        ordering = ['-session_start']
    
    def __str__(self):
        return f"Activity: {self.user_identifier} - {self.session_start}"
    
    def update_session_duration(self):
        """Update session duration based on last activity"""
        if self.last_activity and self.session_start:
            delta = self.last_activity - self.session_start
            self.session_duration = int(delta.total_seconds())


class PopularContent(models.Model):
    """
    Track popular content (comments, files, etc.)
    """
    CONTENT_TYPES = (
        ('comment', 'Comment'),
        ('file', 'File'),
        ('user', 'User'),
    )
    
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPES,
        help_text="Type of content"
    )
    
    content_id = models.PositiveIntegerField(
        help_text="ID of the content item"
    )
    
    content_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Title or name of the content"
    )
    
    # Popularity metrics
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of views"
    )
    
    like_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of likes"
    )
    
    share_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of shares"
    )
    
    comment_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of comments/replies"
    )
    
    # Calculated popularity score
    popularity_score = models.FloatField(
        default=0.0,
        help_text="Calculated popularity score"
    )
    
    # Time tracking
    date = models.DateField(
        default=timezone.now,
        help_text="Date for these metrics"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        db_table = 'analytics_popular_content'
        unique_together = ('content_type', 'content_id', 'date')
        indexes = [
            models.Index(fields=['content_type', 'popularity_score']),
            models.Index(fields=['date', 'popularity_score']),
        ]
        ordering = ['-popularity_score', '-date']
    
    def __str__(self):
        return f"{self.content_type} {self.content_id} - Score: {self.popularity_score}"
    
    def calculate_popularity_score(self):
        """
        Calculate popularity score based on various metrics
        """
        # Weighted score calculation
        score = (
            self.view_count * 1.0 +
            self.like_count * 3.0 +
            self.share_count * 5.0 +
            self.comment_count * 2.0
        )
        
        # Time decay factor (newer content gets slight boost)
        days_old = (timezone.now().date() - self.date).days
        if days_old < 7:
            score *= 1.2
        elif days_old < 30:
            score *= 1.1
        
        self.popularity_score = score
        return score


class SearchQuery(models.Model):
    """
    Track search queries for analytics
    """
    query = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Search query string"
    )
    
    # User information
    user_identifier = models.CharField(
        max_length=255,
        blank=True,
        help_text="User identifier"
    )
    
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of the searcher"
    )
    
    # Search metadata
    results_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of search results returned"
    )
    
    response_time = models.FloatField(
        default=0.0,
        help_text="Search response time in milliseconds"
    )
    
    # User behavior
    clicked_result = models.BooleanField(
        default=False,
        help_text="Whether user clicked on any result"
    )
    
    clicked_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Position of clicked result"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    class Meta:
        db_table = 'analytics_search_queries'
        indexes = [
            models.Index(fields=['query', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['results_count']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search: {self.query} ({self.results_count} results)"
