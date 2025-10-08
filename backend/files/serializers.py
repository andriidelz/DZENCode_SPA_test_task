from rest_framework import serializers
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import FileUpload, FileThumbnail, FileDownload
import mimetypes


class FileThumbnailSerializer(serializers.ModelSerializer):
    """
    Serializer for FileThumbnail model
    """
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = FileThumbnail
        fields = ['size', 'url', 'width', 'height']
    
    def get_url(self, obj):
        """Get thumbnail URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


class FileUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for FileUpload model
    """
    file_url = serializers.SerializerMethodField()
    file_size_human = serializers.ReadOnlyField()
    thumbnails = FileThumbnailSerializer(many=True, read_only=True)
    download_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'name', 'file_type', 'file_size', 'file_size_human',
            'mime_type', 'width', 'height', 'duration',
            'uploaded_at', 'is_public', 'alt_text', 'description', 'tags',
            'file_url', 'thumbnails', 'download_count'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'mime_type', 'width', 'height',
            'uploaded_at', 'file_url', 'thumbnails', 'download_count'
        ]
    
    def get_file_url(self, obj):
        """Get file URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_download_count(self, obj):
        """Get download count"""
        return obj.downloads.count()
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size cannot exceed 10MB."
            )
        
        # Check file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        if hasattr(value, 'content_type'):
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    f"File type {value.content_type} is not allowed."
                )
        
        return value
    
    def create(self, validated_data):
        """Create file upload with metadata"""
        request = self.context.get('request')
        
        if request:
            # Set uploaded_by if user is authenticated
            if request.user.is_authenticated:
                validated_data['uploaded_by'] = request.user
            
            # Set IP address
            validated_data['ip_address'] = self.get_client_ip(request)
            
            # Set MIME type
            file_obj = validated_data.get('file')
            if file_obj:
                mime_type, _ = mimetypes.guess_type(file_obj.name)
                validated_data['mime_type'] = mime_type or 'application/octet-stream'
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FileUploadCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for file uploads
    """
    file = serializers.FileField()
    
    class Meta:
        model = FileUpload
        fields = ['file', 'name', 'alt_text', 'description', 'tags', 'is_public']
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size cannot exceed 10MB."
            )
        return value
    
    def create(self, validated_data):
        """Create file upload with metadata"""
        request = self.context.get('request')
        
        if request:
            if request.user.is_authenticated:
                validated_data['uploaded_by'] = request.user
            
            validated_data['ip_address'] = self.get_client_ip(request)
            
            file_obj = validated_data.get('file')
            if file_obj:
                mime_type, _ = mimetypes.guess_type(file_obj.name)
                validated_data['mime_type'] = mime_type or 'application/octet-stream'
                
                # Set name from filename if not provided
                if not validated_data.get('name'):
                    validated_data['name'] = file_obj.name
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FileDownloadSerializer(serializers.ModelSerializer):
    """
    Serializer for FileDownload model
    """
    file_name = serializers.CharField(source='file_upload.name', read_only=True)
    downloaded_by_username = serializers.CharField(
        source='downloaded_by.username', 
        read_only=True
    )
    
    class Meta:
        model = FileDownload
        fields = [
            'id', 'file_name', 'downloaded_by_username',
            'ip_address', 'downloaded_at'
        ]
        read_only_fields = ['id', 'downloaded_at']


class FileStatsSerializer(serializers.Serializer):
    """
    Serializer for file statistics
    """
    total_files = serializers.IntegerField()
    total_size = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    files_by_type = serializers.DictField()
    recent_uploads = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    popular_files = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
