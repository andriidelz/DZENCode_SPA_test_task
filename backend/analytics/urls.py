from django.urls import path
from . import views

urlpatterns = [
    # Event tracking
    path('events/', views.AnalyticsEventCreateView.as_view(), name='analytics-event-create'),
    path('track/', views.track_event, name='analytics-track-event'),
    
    # Statistics
    path('daily-stats/', views.DailyStatsListView.as_view(), name='analytics-daily-stats'),
    path('popular-content/', views.PopularContentListView.as_view(), name='analytics-popular-content'),
    
    # Dashboard
    path('dashboard/', views.analytics_dashboard, name='analytics-dashboard'),
    path('real-time/', views.real_time_stats, name='analytics-real-time'),
]
