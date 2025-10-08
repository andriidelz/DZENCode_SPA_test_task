from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from PIL import Image
import os


class UploadedFile(models.Model):
    """
    Base model for all uploaded files
    """
    FILE_TYPES = (
        ('image', 'Image'),
        ('text', 'Text File'),
        ('document', 'Document'),
        ('other', 'Other'),
    )
    
    UPLOAD_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    file = models.FileField(
        upload_to='uploads/%Y/%m/%d/',
        help_text="Uploaded file"
    )
    
    original_name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        help_text="Type of the uploaded file"
    )
    
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type of the file"
    )
    
    checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text="MD5 checksum of the file"
    )
    
    # Upload metadata
    uploaded_by_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of uploader"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=UPLOAD_STATUS,
        default='pending',
        help_text="Processing status"
    )
    
    processing_error = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing was completed"
    )
    
    class Meta:
        db_table = 'uploaded_files'
        indexes = [
            models.Index(fields=['file_type', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['checksum']),
        ]
    
    def __str__(self):
        return f"{self.original_name} ({self.file_type})"
    
    def get_file_url(self, request=None):
        """Get full URL for the file"""
        if self.file:
            if request:
                return request.build_absolute_uri(self.file.url)
            return self.file.url
        return None
    
    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted"""
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)


class ImageFile(models.Model):
    """
    Specific model for image files with additional metadata
    """
    uploaded_file = models.OneToOneField(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='image_metadata'
    )
    
    # Original image dimensions
    original_width = models.PositiveIntegerField(
        help_text="Original image width in pixels"
    )
    
    original_height = models.PositiveIntegerField(
        help_text="Original image height in pixels"
    )
    
    # Processed image dimensions (after resizing)
    width = models.PositiveIntegerField(
        help_text="Processed image width in pixels"
    )
    
    height = models.PositiveIntegerField(
        help_text="Processed image height in pixels"
    )
    
    # Image format
    format = models.CharField(
        max_length=10,
        help_text="Image format (JPEG, PNG, GIF)"
    )
    
    # Quality settings
    quality = models.PositiveIntegerField(
        default=85,
        help_text="JPEG quality (1-100)"
    )
    
    # Thumbnail
    thumbnail = models.ImageField(
        upload_to='thumbnails/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Generated thumbnail"
    )
    
    # Image analysis
    has_transparency = models.BooleanField(
        default=False,
        help_text="Whether image has transparency"
    )
    
    color_mode = models.CharField(
        max_length=10,
        blank=True,
        help_text="Image color mode (RGB, RGBA, L, etc.)"
    )
    
    # EXIF data (JSON field would be better but keeping simple)
    exif_data = models.TextField(
        blank=True,
        help_text="EXIF data as JSON string"
    )
    
    class Meta:
        db_table = 'image_files'
    
    def __str__(self):
        return f"Image: {self.uploaded_file.original_name} ({self.width}x{self.height})"
    
    def get_aspect_ratio(self):
        """Get image aspect ratio"""
        if self.height > 0:
            return self.width / self.height
        return 0
    
    def is_landscape(self):
        """Check if image is landscape orientation"""
        return self.width > self.height
    
    def is_portrait(self):
        """Check if image is portrait orientation"""
        return self.height > self.width
    
    def is_square(self):
        """Check if image is square"""
        return self.width == self.height


class TextFile(models.Model):
    """
    Specific model for text files with content preview
    """
    uploaded_file = models.OneToOneField(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='text_metadata'
    )
    
    # Text analysis
    encoding = models.CharField(
        max_length=20,
        default='utf-8',
        help_text="Text file encoding"
    )
    
    line_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of lines in the file"
    )
    
    word_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of words in the file"
    )
    
    character_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of characters in the file"
    )
    
    # Content preview (first few lines)
    preview = models.TextField(
        blank=True,
        help_text="Preview of file content (first 1000 characters)"
    )
    
    # Content validation
    is_valid_utf8 = models.BooleanField(
        default=True,
        help_text="Whether file contains valid UTF-8"
    )
    
    has_binary_content = models.BooleanField(
        default=False,
        help_text="Whether file contains binary data"
    )
    
    class Meta:
        db_table = 'text_files'
    
    def __str__(self):
        return f"Text: {self.uploaded_file.original_name} ({self.line_count} lines)"


class FileUploadLog(models.Model):
    """
    Log of file upload events for monitoring and debugging
    """
    LOG_LEVELS = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )
    
    uploaded_file = models.ForeignKey(
        UploadedFile,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    level = models.CharField(
        max_length=10,
        choices=LOG_LEVELS,
        default='info'
    )
    
    message = models.TextField(
        help_text="Log message"
    )
    
    details = models.TextField(
        blank=True,
        help_text="Additional details (JSON, stack trace, etc.)"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now
    )
    
    class Meta:
        db_table = 'file_upload_logs'
        indexes = [
            models.Index(fields=['uploaded_file', 'created_at']),
            models.Index(fields=['level', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.level.upper()}: {self.message[:50]}..."
