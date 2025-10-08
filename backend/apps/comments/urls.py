from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'comments'

urlpatterns = [
    # Comments CRUD
    path('comments/', views.CommentListCreateView.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
    path('comments/<int:parent_id>/reply/', views.CommentReplyCreateView.as_view(), name='comment-reply'),
    
    # Comment interactions
    path('comments/<int:comment_id>/like/', views.CommentLikeCreateView.as_view(), name='comment-like'),
    
    # CAPTCHA
    path('captcha/generate/', views.generate_captcha, name='captcha-generate'),
    path('captcha/image/<str:token>/', views.captcha_image, name='captcha-image'),
    
    # Utilities
    path('comments/preview/', views.preview_comment, name='comment-preview'),
    path('comments/stats/', views.comment_stats, name='comment-stats'),
]
