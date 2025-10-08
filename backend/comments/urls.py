from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# URL patterns for comments app
urlpatterns = [
    # Comment CRUD operations
    path('', views.CommentListCreateView.as_view(), name='comment-list-create'),
    path('<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
    
    # Comment interactions
    path('<int:comment_id>/like/', views.toggle_comment_like, name='comment-like'),
    path('<int:comment_id>/report/', views.report_comment, name='comment-report'),
    
    # Analytics and stats
    path('stats/', views.comment_stats, name='comment-stats'),
    
    # Health check
    path('health/', views.health_check, name='health-check'),
]
