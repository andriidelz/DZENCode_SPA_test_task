from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/login/', views.UserLoginView.as_view(), name='login'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    
    # User profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/preferences/', views.UserPreferencesView.as_view(), name='preferences'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('profile/stats/', views.user_stats, name='user-stats'),
    path('profile/activity/', views.user_activity, name='user-activity'),
    
    # Public profiles
    path('users/<str:username>/', views.public_user_profile, name='public-profile'),
]
