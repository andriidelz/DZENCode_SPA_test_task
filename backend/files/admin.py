from django.contrib import admin
from .models import FileUpload, FileThumbnail, FileDownload


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    """
    Admin interface for FileUpload model
    """
    list_display = [
        'id', 'name', 'file_type', 'file_size_human', 'uploaded_by',
        'uploaded_at', 'is_public', 'is_active', 'download_count'
    ]
    list_filter = [
        'file_type', 'is_public', 'is_active', 'uploaded_at'
    ]
    search_fields = [
        'name', 'description', 'tags', 'uploaded_by__username'
    ]
    readonly_fields = [
        'id', 'file_size', 'mime_type', 'width', 'height',
        'uploaded_at', 'ip_address', 'file_url', 'download_count'
    ]
    ordering = ['-uploaded_at']
    list_per_page = 50
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        ('File Information', {
            'fields': ('name', 'file', 'file_type', 'file_size', 'mime_type')
        }),
        ('Image Metadata', {
            'fields': ('width', 'height', 'alt_text'),
            'classes': ('collapse',)
        }),
        ('Content', {
            'fields': ('description', 'tags')
        }),
        ('Permissions', {
            'fields': ('is_public', 'is_active')
        }),
        ('Upload Information', {
            'fields': ('uploaded_by', 'uploaded_at', 'ip_address'),
            'classes': ('collapse',)
        })
    )
    
    def file_size_human(self, obj):
        """Show human readable file size"""
        return obj.file_size_human
    file_size_human.short_description = 'File Size'
    
    def download_count(self, obj):
        """Show download count"""
        return obj.downloads.count()
    download_count.short_description = 'Downloads'
    
    def file_url(self, obj):
        """Show file URL"""
        if obj.file:
            return obj.file.url
        return None
    file_url.short_description = 'File URL'
    
    actions = ['mark_public', 'mark_private', 'mark_active', 'mark_inactive']
    
    def mark_public(self, request, queryset):
        """Mark selected files as public"""
        queryset.update(is_public=True)
        self.message_user(request, f'{queryset.count()} files marked as public.')
    mark_public.short_description = 'Mark selected files as public'
    
    def mark_private(self, request, queryset):
        """Mark selected files as private"""
        queryset.update(is_public=False)
        self.message_user(request, f'{queryset.count()} files marked as private.')
    mark_private.short_description = 'Mark selected files as private'
    
    def mark_active(self, request, queryset):
        """Mark selected files as active"""
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} files marked as active.')
    mark_active.short_description = 'Mark selected files as active'
    
    def mark_inactive(self, request, queryset):
        """Mark selected files as inactive"""
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} files marked as inactive.')
    mark_inactive.short_description = 'Mark selected files as inactive'


@admin.register(FileThumbnail)
class FileThumbnailAdmin(admin.ModelAdmin):
    """
    Admin interface for FileThumbnail model
    """
    list_display = [
        'id', 'file_name', 'size', 'width', 'height', 'created_at'
    ]
    list_filter = [
        'size', 'created_at'
    ]
    search_fields = [
        'file_upload__name'
    ]
    readonly_fields = [
        'id', 'file_upload', 'thumbnail', 'width', 'height', 'created_at'
    ]
    ordering = ['-created_at']
    
    def file_name(self, obj):
        """Show original file name"""
        return obj.file_upload.name
    file_name.short_description = 'File Name'


@admin.register(FileDownload)
class FileDownloadAdmin(admin.ModelAdmin):
    """
    Admin interface for FileDownload model
    """
    list_display = [
        'id', 'file_name', 'downloaded_by', 'ip_address', 'downloaded_at'
    ]
    list_filter = [
        'downloaded_at'
    ]
    search_fields = [
        'file_upload__name', 'downloaded_by__username', 'ip_address'
    ]
    readonly_fields = [
        'id', 'file_upload', 'downloaded_by', 'ip_address',
        'user_agent', 'referer', 'downloaded_at'
    ]
    ordering = ['-downloaded_at']
    date_hierarchy = 'downloaded_at'
    
    def file_name(self, obj):
        """Show downloaded file name"""
        return obj.file_upload.name
    file_name.short_description = 'File Name'
    
    def has_add_permission(self, request):
        """Disable adding downloads manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable changing downloads"""
        return False
