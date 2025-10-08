from django.urls import path
from . import views

# URL patterns for users app
urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.user_login, name='user-login'),
    path('logout/', views.user_logout, name='user-logout'),
    
    # Profile management
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('activity/', views.UserActivityListView.as_view(), name='user-activity'),
    
    # Statistics
    path('stats/', views.user_stats, name='user-stats'),
]
