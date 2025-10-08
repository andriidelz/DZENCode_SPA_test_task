from rest_framework import serializers
from django.utils import timezone
from .models import Comment, CommentLike, CommentReport
from django.core.validators import EmailValidator
import re


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for Comment model
    """
    likes_count = serializers.ReadOnlyField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'author', 'email', 'content', 'created_at', 
            'updated_at', 'likes_count', 'is_liked'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'likes_count']
    
    def get_is_liked(self, obj):
        """
        Check if the current IP has liked this comment
        """
        request = self.context.get('request')
        if request:
            ip_address = self.get_client_ip(request)
            return CommentLike.objects.filter(
                comment=obj,
                ip_address=ip_address,
                is_active=True
            ).exists()
        return False
    
    def get_client_ip(self, request):
        """
        Get the client IP address from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def validate_author(self, value):
        """
        Validate author name
        """
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Author name must be at least 2 characters long."
            )
        if len(value.strip()) > 100:
            raise serializers.ValidationError(
                "Author name cannot exceed 100 characters."
            )
        # Check for suspicious patterns
        if re.search(r'[<>"\']', value):
            raise serializers.ValidationError(
                "Author name contains invalid characters."
            )
        return value.strip()
    
    def validate_content(self, value):
        """
        Validate comment content
        """
        content = value.strip()
        if len(content) < 10:
            raise serializers.ValidationError(
                "Comment must be at least 10 characters long."
            )
        if len(content) > 2000:
            raise serializers.ValidationError(
                "Comment cannot exceed 2000 characters."
            )
        # Basic spam detection
        spam_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'\b(?:click here|buy now|free|urgent|act now)\b',
        ]
        for pattern in spam_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                raise serializers.ValidationError(
                    "Comment appears to contain spam content."
                )
        return content
    
    def validate_email(self, value):
        """
        Validate email address
        """
        validator = EmailValidator()
        validator(value)
        return value.lower().strip()
    
    def create(self, validated_data):
        """
        Create a new comment with additional metadata
        """
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            
            # Associate with user if authenticated
            if request.user.is_authenticated:
                validated_data['user'] = request.user
        
        return super().create(validated_data)


class CommentLikeSerializer(serializers.ModelSerializer):
    """
    Serializer for CommentLike model
    """
    class Meta:
        model = CommentLike
        fields = ['id', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        """
        Create a new like with IP tracking
        """
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            
            if request.user.is_authenticated:
                validated_data['user'] = request.user
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """
        Get the client IP address from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CommentReportSerializer(serializers.ModelSerializer):
    """
    Serializer for CommentReport model
    """
    class Meta:
        model = CommentReport
        fields = [
            'id', 'comment', 'reason', 'description', 
            'reporter_email', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_description(self, value):
        """
        Validate report description
        """
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError(
                "Description cannot exceed 500 characters."
            )
        return value.strip() if value else ''
    
    def create(self, validated_data):
        """
        Create a new report with IP tracking
        """
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """
        Get the client IP address from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CommentStatsSerializer(serializers.Serializer):
    """
    Serializer for comment statistics
    """
    total_comments = serializers.IntegerField()
    total_likes = serializers.IntegerField()
    comments_today = serializers.IntegerField()
    comments_this_week = serializers.IntegerField()
    comments_this_month = serializers.IntegerField()
    top_authors = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
    recent_activity = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
