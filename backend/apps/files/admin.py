from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import UploadedFile, ImageFile, TextFile, FileUploadLog
from .services import FileCleanupService


class FileUploadLogInline(admin.TabularInline):
    """
    Inline admin for file upload logs
    """
    model = FileUploadLog
    extra = 0
    readonly_fields = ['level', 'message', 'details', 'created_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """
    Admin interface for uploaded files
    """
    list_display = [
        'id', 'original_name', 'file_type', 'file_size_display',
        'status', 'uploaded_by_ip', 'created_at', 'file_link'
    ]
    
    list_filter = [
        'file_type', 'status', 'created_at', 'mime_type'
    ]
    
    search_fields = [
        'original_name', 'uploaded_by_ip', 'checksum'
    ]
    
    readonly_fields = [
        'file_size', 'mime_type', 'checksum', 'uploaded_by_ip',
        'user_agent', 'created_at', 'processed_at', 'file_link'
    ]
    
    fieldsets = (
        ('File Information', {
            'fields': (
                'file', 'original_name', 'file_type', 'file_size',
                'mime_type', 'checksum'
            )
        }),
        ('Upload Details', {
            'fields': (
                'uploaded_by_ip', 'user_agent', 'created_at'
            )
        }),
        ('Processing', {
            'fields': (
                'status', 'processed_at', 'processing_error'
            )
        }),
        ('Links', {
            'fields': ('file_link',)
        })
    )
    
    inlines = [FileUploadLogInline]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    actions = ['reprocess_files', 'mark_as_completed']
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    file_size_display.short_description = 'File Size'
    
    def file_link(self, obj):
        """Display link to download file"""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download</a>',
                obj.file.url
            )
        return '-'
    file_link.short_description = 'File Link'
    
    def reprocess_files(self, request, queryset):
        """Reprocess selected files"""
        # Implementation would trigger reprocessing
        self.message_user(
            request,
            f'Reprocessing {queryset.count()} files (feature not implemented yet).'
        )
    reprocess_files.short_description = 'Reprocess selected files'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected files as completed"""
        updated = queryset.update(status='completed')
        self.message_user(
            request,
            f'{updated} files marked as completed.'
        )
    mark_as_completed.short_description = 'Mark as completed'


@admin.register(ImageFile)
class ImageFileAdmin(admin.ModelAdmin):
    """
    Admin interface for image files
    """
    list_display = [
        'id', 'uploaded_file_link', 'dimensions_display',
        'format', 'quality', 'has_transparency', 'thumbnail_preview'
    ]
    
    list_filter = [
        'format', 'has_transparency', 'quality', 'color_mode'
    ]
    
    search_fields = [
        'uploaded_file__original_name'
    ]
    
    readonly_fields = [
        'uploaded_file', 'original_width', 'original_height',
        'width', 'height', 'format', 'quality', 'has_transparency',
        'color_mode', 'exif_data', 'thumbnail_preview'
    ]
    
    def uploaded_file_link(self, obj):
        """Display link to uploaded file admin"""
        url = reverse('admin:files_uploadedfile_change', args=[obj.uploaded_file.id])
        return format_html('<a href="{}">{}</a>', url, obj.uploaded_file.original_name)
    uploaded_file_link.short_description = 'File'
    
    def dimensions_display(self, obj):
        """Display image dimensions"""
        return f"{obj.width} × {obj.height}"
    dimensions_display.short_description = 'Dimensions'
    
    def thumbnail_preview(self, obj):
        """Display thumbnail preview"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;"/>',
                obj.thumbnail.url
            )
        return '-'
    thumbnail_preview.short_description = 'Thumbnail'


@admin.register(TextFile)
class TextFileAdmin(admin.ModelAdmin):
    """
    Admin interface for text files
    """
    list_display = [
        'id', 'uploaded_file_link', 'encoding', 'line_count',
        'word_count', 'is_valid_utf8', 'has_binary_content'
    ]
    
    list_filter = [
        'encoding', 'is_valid_utf8', 'has_binary_content'
    ]
    
    search_fields = [
        'uploaded_file__original_name', 'preview'
    ]
    
    readonly_fields = [
        'uploaded_file', 'encoding', 'line_count', 'word_count',
        'character_count', 'is_valid_utf8', 'has_binary_content',
        'preview_display'
    ]
    
    fieldsets = (
        ('File Information', {
            'fields': ('uploaded_file',)
        }),
        ('Text Analysis', {
            'fields': (
                'encoding', 'line_count', 'word_count', 'character_count',
                'is_valid_utf8', 'has_binary_content'
            )
        }),
        ('Content Preview', {
            'fields': ('preview_display',)
        })
    )
    
    def uploaded_file_link(self, obj):
        """Display link to uploaded file admin"""
        url = reverse('admin:files_uploadedfile_change', args=[obj.uploaded_file.id])
        return format_html('<a href="{}">{}</a>', url, obj.uploaded_file.original_name)
    uploaded_file_link.short_description = 'File'
    
    def preview_display(self, obj):
        """Display content preview"""
        if obj.preview:
            return format_html(
                '<pre style="max-height: 300px; overflow-y: scroll; background: #f8f8f8; padding: 10px;">{}</pre>',
                obj.preview
            )
        return '-'
    preview_display.short_description = 'Content Preview'


@admin.register(FileUploadLog)
class FileUploadLogAdmin(admin.ModelAdmin):
    """
    Admin interface for file upload logs
    """
    list_display = [
        'id', 'uploaded_file_link', 'level', 'message_preview',
        'created_at'
    ]
    
    list_filter = [
        'level', 'created_at'
    ]
    
    search_fields = [
        'uploaded_file__original_name', 'message', 'details'
    ]
    
    readonly_fields = [
        'uploaded_file', 'level', 'message', 'details', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def uploaded_file_link(self, obj):
        """Display link to uploaded file admin"""
        url = reverse('admin:files_uploadedfile_change', args=[obj.uploaded_file.id])
        return format_html('<a href="{}">{}</a>', url, obj.uploaded_file.original_name)
    uploaded_file_link.short_description = 'File'
    
    def message_preview(self, obj):
        """Display truncated message"""
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'
    
    def has_add_permission(self, request):
        return False
