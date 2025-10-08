from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, URLValidator, EmailValidator
from django.utils.html import strip_tags
from django.utils import timezone
import bleach
import re


class Comment(models.Model):
    """
    Main comment model with hierarchical structure support
    """
    # User information
    user_name = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9]+$',
                message='User name can only contain letters and numbers'
            )
        ],
        help_text="Username (letters and numbers only)"
    )
    
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text="Valid email address"
    )
    
    home_page = models.URLField(
        blank=True,
        null=True,
        validators=[URLValidator()],
        help_text="Home page URL (optional)"
    )
    
    # Comment content
    text = models.TextField(
        help_text="Comment text (HTML tags will be sanitized)"
    )
    
    sanitized_text = models.TextField(
        blank=True,
        help_text="Sanitized version of the comment text"
    )
    
    # Hierarchical structure
    parent = models.ForeignKey(
        'self',
        on_blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='replies',
        help_text="Parent comment for nested replies"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the comment was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the comment was last updated"
    )
    
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of the commenter"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    # Status and moderation
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the comment is visible"
    )
    
    is_moderated = models.BooleanField(
        default=False,
        help_text="Whether the comment has been moderated"
    )
    
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_comments',
        help_text="User who moderated this comment"
    )
    
    moderated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the comment was moderated"
    )
    
    # Analytics
    likes_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of likes"
    )
    
    replies_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of replies"
    )
    
    class Meta:
        db_table = 'comments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at', 'is_active']),
            models.Index(fields=['parent', 'created_at']),
            models.Index(fields=['user_name', 'created_at']),
            models.Index(fields=['email', 'created_at']),
        ]
        
    def __str__(self):
        return f"{self.user_name}: {self.text[:50]}..."
    
    def save(self, *args, **kwargs):
        """Sanitize text content before saving"""
        self.sanitized_text = self.sanitize_text(self.text)
        super().save(*args, **kwargs)
    
    def sanitize_text(self, text):
        """
        Sanitize HTML content, allowing only specific tags
        """
        allowed_tags = ['i', 'strong', 'code', 'a']
        allowed_attributes = {
            'a': ['href', 'title'],
        }
        
        # First pass: bleach to clean HTML
        cleaned = bleach.clean(
            text,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
        
        # Validate that tags are properly closed (basic XHTML validation)
        if not self.is_valid_xhtml(cleaned):
            # If not valid XHTML, strip all tags
            cleaned = strip_tags(cleaned)
        
        return cleaned
    
    def is_valid_xhtml(self, text):
        """
        Basic XHTML validation to ensure tags are properly closed
        """
        try:
            # Stack to track open tags
            tag_stack = []
            
            # Find all tags
            tag_pattern = r'<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*>'
            tags = re.findall(tag_pattern, text)
            
            for is_closing, tag_name in tags:
                tag_name = tag_name.lower()
                
                if is_closing:  # Closing tag
                    if not tag_stack or tag_stack[-1] != tag_name:
                        return False
                    tag_stack.pop()
                else:  # Opening tag
                    # Skip self-closing tags like <br/>, <img/>
                    if not text[text.find(f'<{tag_name}'):text.find('>', text.find(f'<{tag_name}')) + 1].endswith('/>'):
                        tag_stack.append(tag_name)
            
            return len(tag_stack) == 0
        except:
            return False
    
    def get_thread_comments(self):
        """
        Get all comments in the same thread (including nested replies)
        """
        if self.parent:
            return self.parent.get_thread_comments()
        return Comment.objects.filter(
            models.Q(id=self.id) | models.Q(parent=self)
        ).select_related('parent')
    
    def get_depth(self):
        """
        Get the depth of this comment in the thread
        """
        depth = 0
        parent = self.parent
        while parent:
            depth += 1
            parent = parent.parent
        return depth
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    @property
    def can_reply(self):
        """Comments can have maximum 3 levels of nesting"""
        return self.get_depth() < 3


class CommentLike(models.Model):
    """
    Model to track likes on comments
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
        blank=True,
        help_text="User agent string"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    class Meta:
        db_table = 'comment_likes'
        unique_together = ('comment', 'ip_address')
        indexes = [
            models.Index(fields=['comment', 'created_at']),
        ]
    
    def __str__(self):
        return f"Like on {self.comment.id} from {self.ip_address}"


class CommentFile(models.Model):
    """
    Model for files attached to comments
    """
    FILE_TYPES = (
        ('image', 'Image'),
        ('text', 'Text File'),
    )
    
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='files'
    )
    
    file = models.FileField(
        upload_to='comment_files/%Y/%m/%d/',
        help_text="Uploaded file"
    )
    
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPES,
        help_text="Type of the uploaded file"
    )
    
    original_name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    class Meta:
        db_table = 'comment_files'
        indexes = [
            models.Index(fields=['comment', 'file_type']),
        ]
    
    def __str__(self):
        return f"{self.original_name} ({self.file_type})"


class CaptchaToken(models.Model):
    """
    Model to store CAPTCHA tokens and their solutions
    """
    token = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Unique CAPTCHA token"
    )
    
    challenge = models.CharField(
        max_length=10,
        help_text="CAPTCHA challenge text"
    )
    
    solution = models.CharField(
        max_length=10,
        help_text="CAPTCHA solution"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the CAPTCHA was used"
    )
    
    ip_address = models.GenericIPAddressField(
        help_text="IP address that requested the CAPTCHA"
    )
    
    class Meta:
        db_table = 'captcha_tokens'
        indexes = [
            models.Index(fields=['token', 'created_at']),
        ]
    
    @property
    def is_expired(self):
        """CAPTCHA expires after 10 minutes"""
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=10)
    
    @property
    def is_used(self):
        return self.used_at is not None
    
    def __str__(self):
        return f"CAPTCHA {self.token} - {self.challenge}"
