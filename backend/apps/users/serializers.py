from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserPreference


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'bio', 'website'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        
        # Create default preferences
        UserPreference.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information
    """
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'bio', 'website', 'avatar', 'avatar_url', 'comments_count',
            'likes_received', 'date_joined', 'last_login', 'show_email'
        ]
        read_only_fields = [
            'id', 'comments_count', 'likes_received', 'date_joined', 'last_login'
        ]
        extra_kwargs = {
            'email': {'required': False}
        }
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for user preferences
    """
    class Meta:
        model = UserPreference
        fields = [
            'theme', 'language', 'comments_per_page',
            'email_on_reply', 'email_on_like', 'email_digest'
        ]


class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for user statistics
    """
    total_comments = serializers.IntegerField()
    total_likes_received = serializers.IntegerField()
    total_replies_received = serializers.IntegerField()
    most_liked_comment = serializers.DictField()
    recent_activity = serializers.ListField()
    join_date = serializers.DateTimeField()
    last_comment_date = serializers.DateTimeField(allow_null=True)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user password
    """
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect')
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class TokenSerializer(serializers.Serializer):
    """
    Serializer for JWT tokens
    """
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserProfileSerializer()
