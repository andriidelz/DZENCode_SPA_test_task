from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.validators import validate_email
from .models import UserProfile, UserActivity
import re


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile model
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.CharField(read_only=True)
    public_name = serializers.CharField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'display_name', 'bio', 
            'avatar', 'website', 'location', 'birth_date',
            'is_email_public', 'is_profile_public',
            'email_notifications', 'comment_notifications',
            'full_name', 'public_name', 'comment_count',
            'created_at', 'updated_at', 'last_active'
        ]
        read_only_fields = [
            'id', 'username', 'email', 'full_name', 'public_name', 
            'comment_count', 'created_at', 'updated_at'
        ]
    
    def validate_display_name(self, value):
        """Validate display name"""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Display name must be at least 2 characters long."
            )
        if value and len(value.strip()) > 100:
            raise serializers.ValidationError(
                "Display name cannot exceed 100 characters."
            )
        return value.strip() if value else ''
    
    def validate_bio(self, value):
        """Validate bio"""
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError(
                "Bio cannot exceed 500 characters."
            )
        return value.strip() if value else ''
    
    def validate_website(self, value):
        """Validate website URL"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(
                "Website URL must start with http:// or https://"
            )
        return value


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name'
        ]
    
    def validate_username(self, value):
        """Validate username"""
        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must be at least 3 characters long."
            )
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, and underscores."
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value
    
    def validate_email(self, value):
        """Validate email"""
        validate_email(value)
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value.lower()
    
    def validate_password(self, value):
        """Validate password strength"""
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter."
            )
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter."
            )
        if not re.search(r'\d', value):
            raise serializers.ValidationError(
                "Password must contain at least one digit."
            )
        return value
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                "Password and password confirmation do not match."
            )
        return attrs
    
    def create(self, validated_data):
        """Create user and profile"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    username = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True
    )
    
    def validate(self, attrs):
        """Validate login credentials"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Try to authenticate with username or email
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                # Try with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(
                        request=self.context.get('request'),
                        username=user_obj.username,
                        password=password
                    )
                except User.DoesNotExist:
                    pass
            
            if not user:
                raise serializers.ValidationError(
                    "Unable to log in with provided credentials."
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    "User account is disabled."
                )
            
            attrs['user'] = user
            return attrs
        
        raise serializers.ValidationError(
            "Must include username and password."
        )


class UserActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for UserActivity model
    """
    username = serializers.CharField(source='user.username', read_only=True)
    activity_display = serializers.CharField(
        source='get_activity_type_display', 
        read_only=True
    )
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'username', 'activity_type', 'activity_display',
            'description', 'timestamp', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']


class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for user statistics
    """
    total_users = serializers.IntegerField()
    active_users_today = serializers.IntegerField()
    active_users_week = serializers.IntegerField()
    new_users_today = serializers.IntegerField()
    new_users_week = serializers.IntegerField()
    top_commenters = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )
