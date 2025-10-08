from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import UploadedFile, ImageFile, TextFile
from .services import FileUploadService
import mimetypes


class UploadedFileSerializer(serializers.ModelSerializer):
    """
    Serializer for uploaded files
    """
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = UploadedFile
        fields = [
            'id', 'original_name', 'file_type', 'file_size',
            'file_size_display', 'mime_type', 'status',
            'created_at', 'processed_at', 'file_url'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'mime_type',
            'status', 'created_at', 'processed_at'
        ]
    
    def get_file_url(self, obj):
        """Get full URL for the file"""
        request = self.context.get('request')
        return obj.get_file_url(request)
    
    def get_file_size_display(self, obj):
        """Get human-readable file size"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class ImageFileSerializer(serializers.ModelSerializer):
    """
    Serializer for image files with metadata
    """
    uploaded_file = UploadedFileSerializer(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    aspect_ratio = serializers.SerializerMethodField()
    orientation = serializers.SerializerMethodField()
    
    class Meta:
        model = ImageFile
        fields = [
            'id', 'uploaded_file', 'original_width', 'original_height',
            'width', 'height', 'format', 'quality', 'thumbnail_url',
            'has_transparency', 'color_mode', 'aspect_ratio', 'orientation'
        ]
        read_only_fields = ['id']
    
    def get_thumbnail_url(self, obj):
        """Get thumbnail URL"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None
    
    def get_aspect_ratio(self, obj):
        """Get aspect ratio"""
        return obj.get_aspect_ratio()
    
    def get_orientation(self, obj):
        """Get image orientation"""
        if obj.is_landscape():
            return 'landscape'
        elif obj.is_portrait():
            return 'portrait'
        else:
            return 'square'


class TextFileSerializer(serializers.ModelSerializer):
    """
    Serializer for text files with metadata
    """
    uploaded_file = UploadedFileSerializer(read_only=True)
    
    class Meta:
        model = TextFile
        fields = [
            'id', 'uploaded_file', 'encoding', 'line_count',
            'word_count', 'character_count', 'preview',
            'is_valid_utf8', 'has_binary_content'
        ]
        read_only_fields = ['id']


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for file upload with validation
    """
    file = serializers.FileField()
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size
        max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 2621440)  # 2.5MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(value.name)
        
        # Validate image files
        if mime_type and mime_type.startswith('image/'):
            allowed_formats = getattr(settings, 'ALLOWED_IMAGE_FORMATS', ['JPEG', 'PNG', 'GIF'])
            
            # Check file extension
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            file_extension = value.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise serializers.ValidationError(
                    f"Image format not allowed. Allowed formats: {', '.join(allowed_extensions)}"
                )
        
        # Validate text files
        elif mime_type and mime_type.startswith('text/'):
            max_text_size = getattr(settings, 'TEXT_FILE_MAX_SIZE', 102400)  # 100KB
            if value.size > max_text_size:
                raise serializers.ValidationError(
                    f"Text file size ({value.size} bytes) exceeds maximum allowed size ({max_text_size} bytes)"
                )
            
            # Check file extension
            allowed_extensions = getattr(settings, 'ALLOWED_TEXT_FORMATS', ['.txt'])
            file_extension = f".{value.name.lower().split('.')[-1]}"
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    f"Text file format not allowed. Allowed formats: {', '.join(allowed_extensions)}"
                )
        
        else:
            raise serializers.ValidationError(
                "File type not supported. Only images and text files are allowed."
            )
        
        return value
    
    def create(self, validated_data):
        """Process and save uploaded file"""
        file = validated_data['file']
        request = self.context.get('request')
        
        # Use FileUploadService to process the file
        file_service = FileUploadService()
        result = file_service.process_upload(file, request=request)
        
        return result


class FileStatsSerializer(serializers.Serializer):
    """
    Serializer for file statistics
    """
    total_files = serializers.IntegerField()
    total_size = serializers.IntegerField()
    total_size_display = serializers.CharField()
    files_by_type = serializers.DictField()
    files_this_week = serializers.IntegerField()
    average_file_size = serializers.FloatField()
    largest_file = serializers.DictField()
    most_recent_upload = serializers.DictField()


class BulkFileUploadSerializer(serializers.Serializer):
    """
    Serializer for bulk file upload
    """
    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=10,  # Limit bulk uploads
        write_only=True
    )
    
    def validate_files(self, value):
        """Validate all files in bulk upload"""
        for file in value:
            # Use single file validator
            file_serializer = FileUploadSerializer()
            file_serializer.validate_file(file)
        
        return value
    
    def create(self, validated_data):
        """Process bulk file upload"""
        files = validated_data['files']
        request = self.context.get('request')
        
        file_service = FileUploadService()
        results = []
        
        for file in files:
            try:
                result = file_service.process_upload(file, request=request)
                results.append({
                    'success': True,
                    'file': result,
                    'error': None
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'file': None,
                    'error': str(e)
                })
        
        return results
