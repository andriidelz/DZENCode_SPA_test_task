from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    # File operations
    path('upload/', views.FileUploadView.as_view(), name='file-upload'),
    path('upload/bulk/', views.BulkFileUploadView.as_view(), name='bulk-file-upload'),
    path('files/', views.FileListView.as_view(), name='file-list'),
    path('files/<int:pk>/', views.FileDetailView.as_view(), name='file-detail'),
    path('files/<int:pk>/download/', views.FileDownloadView.as_view(), name='file-download'),
    
    # File previews
    path('files/<int:file_id>/thumbnail/', views.file_thumbnail, name='file-thumbnail'),
    path('files/<int:file_id>/preview/', views.file_preview, name='file-preview'),
    
    # Statistics and management
    path('files/stats/', views.file_stats, name='file-stats'),
    path('files/cleanup/', views.cleanup_files, name='file-cleanup'),
]
