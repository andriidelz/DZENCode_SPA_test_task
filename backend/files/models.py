from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from PIL import Image
import os
import uuid


def upload_to_path(instance, filename):
    """
    Generate upload path for files
    """
    # Get file extension
    ext = filename.split('.')[-1]
    # Generate unique filename
    filename = f'{uuid.uuid4()}.{ext}'
    # Return upload path
    return os.path.join('uploads', str(timezone.now().year), str(timezone.now().month), filename)


class FileUpload(models.Model):
    """
    Model for file uploads
    """
    FILE_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    file = models.FileField(
        upload_to=upload_to_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',  # Images
                    'pdf', 'doc', 'docx', 'txt', 'rtf',  # Documents
                    'mp4', 'avi', 'mov', 'wmv', 'flv',  # Videos
                    'mp3', 'wav', 'aac', 'flac', 'ogg',  # Audio
                    'zip', 'rar', '7z', 'tar', 'gz'  # Archives
                ]
            )
        ]
    )
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        default='other'
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True
    )
    
    # File metadata
    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Image width in pixels"
    )
    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Image height in pixels"
    )
    duration = models.DurationField(
        null=True,
        blank=True,
        help_text="Video/Audio duration"
    )
    
    # Upload information
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_files'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    
    # File status
    is_public = models.BooleanField(
        default=False,
        help_text="Whether file is publicly accessible"
    )
    is_processed = models.BooleanField(
        default=False,
        help_text="Whether file has been processed (thumbnails, etc.)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether file is active"
    )
    
    # SEO and metadata
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Alt text for images"
    )
    description = models.TextField(
        blank=True,
        help_text="File description"
    )
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated tags"
    )
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['file_type', '-uploaded_at']),
            models.Index(fields=['uploaded_by', '-uploaded_at']),
            models.Index(fields=['is_public', 'is_active']),
        ]
        verbose_name = 'File Upload'
        verbose_name_plural = 'File Uploads'
    
    def __str__(self):
        return f'{self.name} ({self.file_type})'
    
    @property
    def file_url(self):
        """Get file URL"""
        if self.file:
            return self.file.url
        return None
    
    @property
    def file_size_human(self):
        """Get human readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_image(self):
        """Check if file is an image"""
        return self.file_type == 'image'
    
    @property
    def thumbnail_url(self):
        """Get thumbnail URL for images"""
        if self.is_image and hasattr(self, 'thumbnail'):
            return self.thumbnail.thumbnail.url
        return None
    
    def save(self, *args, **kwargs):
        """Override save to set file metadata"""
        if self.file:
            # Set file size
            self.file_size = self.file.size
            
            # Set file type based on extension
            ext = self.file.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
                self.file_type = 'image'
            elif ext in ['pdf', 'doc', 'docx', 'txt', 'rtf']:
                self.file_type = 'document'
            elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv']:
                self.file_type = 'video'
            elif ext in ['mp3', 'wav', 'aac', 'flac', 'ogg']:
                self.file_type = 'audio'
            
            # Set original filename if not set
            if not self.name:
                self.name = self.file.name
        
        super().save(*args, **kwargs)
        
        # Process image metadata after saving
        if self.file_type == 'image' and not self.is_processed:
            self.process_image()
    
    def process_image(self):
        """Process image to extract metadata and create thumbnail"""
        try:
            with Image.open(self.file.path) as img:
                self.width, self.height = img.size
                self.is_processed = True
                self.save(update_fields=['width', 'height', 'is_processed'])
                
                # Create thumbnail
                FileThumbnail.objects.get_or_create(
                    file_upload=self,
                    defaults={'size': 'medium'}
                )
        except Exception as e:
            print(f"Error processing image {self.id}: {e}")


class FileThumbnail(models.Model):
    """
    Model for file thumbnails
    """
    THUMBNAIL_SIZES = [
        ('small', 'Small (150x150)'),
        ('medium', 'Medium (300x300)'),
        ('large', 'Large (600x600)'),
    ]
    
    file_upload = models.ForeignKey(
        FileUpload,
        on_delete=models.CASCADE,
        related_name='thumbnails'
    )
    size = models.CharField(
        max_length=10,
        choices=THUMBNAIL_SIZES,
        default='medium'
    )
    thumbnail = models.ImageField(
        upload_to='thumbnails/%Y/%m/',
        help_text="Generated thumbnail"
    )
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        unique_together = ['file_upload', 'size']
        verbose_name = 'File Thumbnail'
        verbose_name_plural = 'File Thumbnails'
    
    def __str__(self):
        return f'{self.file_upload.name} - {self.size} thumbnail'
    
    def save(self, *args, **kwargs):
        """Generate thumbnail on save"""
        if not self.thumbnail and self.file_upload.is_image:
            self.generate_thumbnail()
        super().save(*args, **kwargs)
    
    def generate_thumbnail(self):
        """Generate thumbnail from original image"""
        if not self.file_upload.file:
            return
        
        # Size mapping
        size_map = {
            'small': (150, 150),
            'medium': (300, 300),
            'large': (600, 600),
        }
        
        target_size = size_map.get(self.size, (300, 300))
        
        try:
            with Image.open(self.file_upload.file.path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumbnail_name = f"{self.file_upload.name}_{self.size}_thumb.jpg"
                thumbnail_path = os.path.join('thumbnails', str(timezone.now().year), str(timezone.now().month), thumbnail_name)
                
                from django.core.files.base import ContentFile
                from io import BytesIO
                
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                buffer.seek(0)
                
                self.thumbnail.save(
                    thumbnail_name,
                    ContentFile(buffer.getvalue()),
                    save=False
                )
                
                self.width, self.height = img.size
                
        except Exception as e:
            print(f"Error generating thumbnail for {self.file_upload.id}: {e}")


class FileDownload(models.Model):
    """
    Track file downloads for analytics
    """
    file_upload = models.ForeignKey(
        FileUpload,
        on_delete=models.CASCADE,
        related_name='downloads'
    )
    downloaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='file_downloads'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(
        blank=True
    )
    referer = models.URLField(
        blank=True,
        help_text="Page that referred to this download"
    )
    downloaded_at = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['file_upload', '-downloaded_at']),
            models.Index(fields=['ip_address', '-downloaded_at']),
        ]
        verbose_name = 'File Download'
        verbose_name_plural = 'File Downloads'
    
    def __str__(self):
        return f'Download of {self.file_upload.name} at {self.downloaded_at}'
