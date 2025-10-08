from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema

from .models import User, UserPreference
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserPreferenceSerializer,
    UserStatsSerializer,
    ChangePasswordSerializer,
    TokenSerializer
)
from .services import UserService


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited user registration"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Register new user",
        description="Create a new user account with JWT token response"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserLoginView(generics.GenericAPIView):
    """
    User login endpoint
    """
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited user login"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update last login
            login(request, user)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="User login",
        description="Authenticate user and return JWT tokens"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile view and update
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        summary="Get user profile",
        description="Get current user's profile information"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update user profile",
        description="Update current user's profile information"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class UserPreferencesView(generics.RetrieveUpdateAPIView):
    """
    User preferences view and update
    """
    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        preferences, created = UserPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    @extend_schema(
        summary="Get user preferences",
        description="Get current user's preferences and settings"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update user preferences",
        description="Update current user's preferences and settings"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ChangePasswordView(generics.GenericAPIView):
    """
    Change user password
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @method_decorator(ratelimit(key='user', rate='5/h', method='POST'))
    def post(self, request, *args, **kwargs):
        """Rate-limited password change"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password changed successfully'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Change password",
        description="Change current user's password"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    summary="Get user statistics",
    description="Get statistics for the current user"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@cache_page(60 * 10)  # Cache for 10 minutes
def user_stats(request):
    """
    Get user statistics
    """
    stats = UserService.get_user_stats(request.user)
    serializer = UserStatsSerializer(stats)
    return Response(serializer.data)


@extend_schema(
    summary="Get public user profile",
    description="Get public profile information for any user"
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_user_profile(request, username):
    """
    Get public user profile by username
    """
    try:
        user = User.objects.get(username=username)
        
        # Only show limited public information
        data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bio': user.bio,
            'website': user.website,
            'date_joined': user.date_joined,
            'comments_count': user.comments_count,
            'likes_received': user.likes_received,
        }
        
        # Only show email if user allows it
        if user.show_email:
            data['email'] = user.email
        
        # Add avatar URL if available
        if user.avatar:
            data['avatar_url'] = request.build_absolute_uri(user.avatar.url)
        
        return Response(data)
    
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    summary="Get user activity",
    description="Get recent activity for the current user"
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_activity(request):
    """
    Get user's recent activity
    """
    activity = UserService.get_user_activity(request.user, limit=20)
    return Response(activity)
