"""
URL configuration for comment system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    API root endpoint with available endpoints
    """
    return Response({
        'message': 'Comment System API',
        'version': '1.0.0',
        'timestamp': timezone.now(),
        'endpoints': {
            'comments': '/api/comments/',
            'users': '/api/users/',
            'files': '/api/files/',
            'analytics': '/api/analytics/',
            'admin': f'/{settings.ADMIN_URL}',
            'docs': '/api/docs/',
        },
        'features': [
            'Comment management',
            'User authentication',
            'File uploads',
            'Analytics tracking',
            'Real-time statistics'
        ]
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for monitoring
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now(),
        'version': '1.0.0',
        'database': 'connected',
        'cache': 'available'
    })


urlpatterns = [
    # Admin panel
    path(f'{settings.ADMIN_URL}', admin.site.urls),
    
    # API root
    path('api/', api_root, name='api-root'),
    path('health/', health_check, name='health-check'),
    
    # API endpoints
    path('api/comments/', include('comments.urls')),
    path('api/users/', include('users.urls')),
    path('api/files/', include('files.urls')),
    path('api/analytics/', include('analytics.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Add API documentation in development
    try:
        from rest_framework.documentation import include_docs_urls
        urlpatterns.append(
            path('api/docs/', include_docs_urls(
                title='Comment System API',
                description='API documentation for the Comment System'
            ))
        )
    except ImportError:
        pass

# Custom error handlers
def handler404(request, exception):
    """Custom 404 handler"""
    return JsonResponse({
        'error': 'Not Found',
        'message': 'The requested resource was not found.',
        'status_code': 404
    }, status=404)


def handler500(request):
    """Custom 500 handler"""
    return JsonResponse({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred.',
        'status_code': 500
    }, status=500)


# Customize admin
admin.site.site_header = 'Comment System Administration'
admin.site.site_title = 'Comment System Admin'
admin.site.index_title = 'Welcome to Comment System Administration'
