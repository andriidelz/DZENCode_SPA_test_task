from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Comment, CommentLike, CommentFile, CaptchaToken
from apps.files.serializers import FileUploadSerializer
import uuid
import random
import string


class CaptchaSerializer(serializers.ModelSerializer):
    """
    Serializer for CAPTCHA generation and validation
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CaptchaToken
        fields = ['token', 'challenge', 'image_url']
        read_only_fields = ['token', 'challenge', 'image_url']
    
    def get_image_url(self, obj):
        """Generate URL for CAPTCHA image"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/captcha/image/{obj.token}/')
        return f'/captcha/image/{obj.token}/'
    
    def create(self, validated_data):
        """Generate new CAPTCHA"""
        # Generate math challenge
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        challenge = f"{num1} + {num2} = ?"
        solution = str(num1 + num2)
        
        # Generate unique token
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        
        # Get IP address from request
        request = self.context.get('request')
        ip_address = self.get_client_ip(request)
        
        return CaptchaToken.objects.create(
            token=token,
            challenge=challenge,
            solution=solution,
            ip_address=ip_address
        )
    
    def get_client_ip(self, request):
        """Extract client IP from request"""
        if not request:
            return '127.0.0.1'
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CommentFileSerializer(serializers.ModelSerializer):
    """
    Serializer for comment file attachments
    """
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = CommentFile
        fields = ['id', 'file_type', 'original_name', 'file_size', 'url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_url(self, obj):
        """Get URL for the file"""
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class CommentSerializer(serializers.ModelSerializer):
    """
    Main serializer for comments with full validation
    """
    replies = serializers.SerializerMethodField()
    files = CommentFileSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    captcha_token = serializers.CharField(write_only=True)
    captcha_solution = serializers.CharField(write_only=True)
    depth = serializers.SerializerMethodField()
    can_reply = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'user_name', 'email', 'home_page', 'text', 'sanitized_text',
            'parent', 'created_at', 'updated_at', 'is_active', 'likes_count',
            'replies_count', 'replies', 'files', 'uploaded_files',
            'captcha_token', 'captcha_solution', 'depth', 'can_reply',
            'formatted_date'
        ]
        read_only_fields = [
            'id', 'sanitized_text', 'created_at', 'updated_at', 'is_active',
            'likes_count', 'replies_count', 'depth', 'can_reply', 'formatted_date'
        ]
        extra_kwargs = {
            'email': {'write_only': True},  # Don't expose emails in API responses
        }
    
    def get_replies(self, obj):
        """Get nested replies for this comment"""
        if obj.replies.exists():
            replies = obj.replies.filter(is_active=True).order_by('created_at')
            return CommentSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_depth(self, obj):
        """Get comment nesting depth"""
        return obj.get_depth()
    
    def get_can_reply(self, obj):
        """Check if this comment can have replies"""
        return obj.can_reply
    
    def get_formatted_date(self, obj):
        """Get formatted date string"""
        return obj.created_at.strftime('%d.%m.%y в %H:%M')
    
    def validate_captcha_token(self, value):
        """Validate CAPTCHA token exists and is not expired"""
        try:
            captcha = CaptchaToken.objects.get(token=value)
            if captcha.is_expired:
                raise serializers.ValidationError("CAPTCHA has expired")
            if captcha.is_used:
                raise serializers.ValidationError("CAPTCHA has already been used")
            return value
        except CaptchaToken.DoesNotExist:
            raise serializers.ValidationError("Invalid CAPTCHA token")
    
    def validate(self, attrs):
        """Cross-field validation including CAPTCHA solution"""
        captcha_token = attrs.get('captcha_token')
        captcha_solution = attrs.get('captcha_solution')
        
        if captcha_token and captcha_solution:
            try:
                captcha = CaptchaToken.objects.get(token=captcha_token)
                if captcha.solution != captcha_solution:
                    raise serializers.ValidationError({
                        'captcha_solution': 'Incorrect CAPTCHA solution'
                    })
            except CaptchaToken.DoesNotExist:
                raise serializers.ValidationError({
                    'captcha_token': 'Invalid CAPTCHA token'
                })
        
        # Validate parent comment
        parent = attrs.get('parent')
        if parent and not parent.can_reply:
            raise serializers.ValidationError({
                'parent': 'Cannot reply to this comment (max nesting level reached)'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create comment with file attachments and CAPTCHA validation"""
        # Remove write-only fields
        uploaded_files = validated_data.pop('uploaded_files', [])
        captcha_token = validated_data.pop('captcha_token')
        captcha_solution = validated_data.pop('captcha_solution')
        
        # Get request metadata
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Create comment
        comment = Comment.objects.create(**validated_data)
        
        # Mark CAPTCHA as used
        try:
            captcha = CaptchaToken.objects.get(token=captcha_token)
            captcha.used_at = timezone.now()
            captcha.save()
        except CaptchaToken.DoesNotExist:
            pass
        
        # Handle file uploads
        self.handle_file_uploads(comment, uploaded_files, request)
        
        # Update parent reply count
        if comment.parent:
            comment.parent.replies_count = comment.parent.replies.count()
            comment.parent.save(update_fields=['replies_count'])
        
        return comment
    
    def handle_file_uploads(self, comment, uploaded_files, request):
        """Handle file uploads for the comment"""
        from apps.files.services import FileUploadService
        
        for uploaded_file in uploaded_files:
            try:
                file_service = FileUploadService()
                processed_file = file_service.process_upload(
                    uploaded_file,
                    request=request
                )
                
                CommentFile.objects.create(
                    comment=comment,
                    file=processed_file['file'],
                    file_type=processed_file['file_type'],
                    original_name=processed_file['original_name'],
                    file_size=processed_file['file_size']
                )
            except Exception as e:
                # Log the error but don't fail the comment creation
                print(f"File upload error: {e}")
    
    def get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CommentListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for comment lists (without nested replies)
    """
    files_count = serializers.SerializerMethodField()
    has_replies = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'user_name', 'home_page', 'sanitized_text', 'parent',
            'created_at', 'likes_count', 'replies_count', 'files_count',
            'has_replies', 'formatted_date'
        ]
    
    def get_files_count(self, obj):
        return obj.files.count()
    
    def get_has_replies(self, obj):
        return obj.replies.filter(is_active=True).exists()
    
    def get_formatted_date(self, obj):
        return obj.created_at.strftime('%d.%m.%y в %H:%M')


class CommentLikeSerializer(serializers.ModelSerializer):
    """
    Serializer for comment likes
    """
    class Meta:
        model = CommentLike
        fields = ['id', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        """Create like with IP tracking"""
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Check if already liked
        comment = validated_data['comment']
        ip_address = validated_data['ip_address']
        
        existing_like = CommentLike.objects.filter(
            comment=comment,
            ip_address=ip_address
        ).first()
        
        if existing_like:
            raise serializers.ValidationError(
                "You have already liked this comment"
            )
        
        like = CommentLike.objects.create(**validated_data)
        
        # Update comment likes count
        comment.likes_count = comment.likes.count()
        comment.save(update_fields=['likes_count'])
        
        return like
    
    def get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
