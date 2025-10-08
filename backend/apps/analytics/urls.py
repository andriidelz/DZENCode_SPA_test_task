from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Dashboard and overview
    path('dashboard/', views.analytics_dashboard, name='analytics-dashboard'),
    path('realtime/', views.realtime_analytics, name='realtime-analytics'),
    path('health/', views.system_health, name='system-health'),
    
    # Data views
    path('stats/daily/', views.DailyStatsListView.as_view(), name='daily-stats'),
    path('events/', views.EventListView.as_view(), name='events-list'),
    path('activity/', views.UserActivityListView.as_view(), name='user-activity'),
    path('popular/', views.PopularContentListView.as_view(), name='popular-content'),
    
    # Search analytics
    path('search/', views.search_analytics, name='search-analytics'),
    
    # User-specific analytics
    path('users/<str:user_identifier>/', views.user_statistics, name='user-statistics'),
    
    # Export
    path('export/', views.export_analytics, name='export-analytics'),
]
