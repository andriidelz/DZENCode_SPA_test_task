from django.urls import path
from . import views

# URL patterns for files app
urlpatterns = [
    # File CRUD operations
    path('', views.FileUploadListCreateView.as_view(), name='file-list-create'),
    path('<int:pk>/', views.FileUploadDetailView.as_view(), name='file-detail'),
    
    # File operations
    path('<int:file_id>/download/', views.download_file, name='file-download'),
    path('<int:file_id>/thumbnail/', views.get_thumbnail, name='file-thumbnail'),
    path('<int:file_id>/thumbnail/<str:size>/', views.get_thumbnail, name='file-thumbnail-size'),
    
    # Statistics
    path('stats/', views.file_stats, name='file-stats'),
]
