from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from .models import UserProfile, UserActivity, UserSession
from .serializers import (
    UserProfileSerializer, UserRegistrationSerializer,
    UserLoginSerializer, UserActivitySerializer, UserStatsSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        """Create user and log activity"""
        user = serializer.save()
        
        # Log registration activity
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            description='User registered',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_login(request):
    """
    User login endpoint
    """
    serializer = UserLoginSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Create or get auth token
        token, created = Token.objects.get_or_create(user=user)
        
        # Update user profile last active
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.last_active = timezone.now()
        profile.save()
        
        # Log login activity
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            description='User logged in',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Get user profile data
        profile_serializer = UserProfileSerializer(profile)
        
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'profile': profile_serializer.data,
            'message': 'Login successful'
        })
    
    return Response(
        serializer.errors, 
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def user_logout(request):
    """
    User logout endpoint
    """
    try:
        # Delete auth token
        request.user.auth_token.delete()
        
        # Log logout activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='logout',
            description='User logged out',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'message': 'Logout successful'
        })
    
    except Exception as e:
        return Response({
            'error': 'Error during logout'
        }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update user profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get current user's profile"""
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile
    
    def perform_update(self, serializer):
        """Log profile update activity"""
        serializer.save()
        
        UserActivity.objects.create(
            user=self.request.user,
            activity_type='profile_update',
            description='User updated profile',
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )


class UserActivityListView(generics.ListAPIView):
    """
    Get user activity history
    """
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get current user's activities"""
        return UserActivity.objects.filter(
            user=self.request.user
        ).order_by('-timestamp')[:50]  # Last 50 activities


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@cache_page(60 * 15)  # Cache for 15 minutes
def user_stats(request):
    """
    Get user statistics
    """
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    
    # Basic stats
    total_users = User.objects.count()
    
    # Active users (users with recent activity)
    active_users_today = UserProfile.objects.filter(
        last_active__date=today
    ).count()
    
    active_users_week = UserProfile.objects.filter(
        last_active__gte=week_ago
    ).count()
    
    # New users
    new_users_today = User.objects.filter(
        date_joined__date=today
    ).count()
    
    new_users_week = User.objects.filter(
        date_joined__gte=week_ago
    ).count()
    
    # Top commenters
    from comments.models import Comment
    top_commenters = User.objects.annotate(
        comment_count=Count('comments', filter=Q(comments__is_active=True))
    ).filter(
        comment_count__gt=0
    ).order_by('-comment_count')[:5]
    
    top_commenters_data = []
    for user in top_commenters:
        profile = getattr(user, 'profile', None)
        top_commenters_data.append({
            'username': user.username,
            'display_name': profile.public_name if profile else user.username,
            'comment_count': user.comment_count,
            'joined': user.date_joined
        })
    
    stats_data = {
        'total_users': total_users,
        'active_users_today': active_users_today,
        'active_users_week': active_users_week,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'top_commenters': top_commenters_data
    }
    
    serializer = UserStatsSerializer(stats_data)
    return Response(serializer.data)


def get_client_ip(request):
    """
    Helper function to get client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
