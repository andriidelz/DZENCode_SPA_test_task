"""
URL configuration for comments project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include('apps.comments.urls')),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.files.urls')),
    path('api/v1/', include('apps.analytics.urls')),
    
    # Authentication
    path('api/auth/', include('rest_framework.urls')),
    
    # GraphQL
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True))),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # CAPTCHA
    path('captcha/', include('captcha.urls')),
    
    # Monitoring
    path('', include('django_prometheus.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
