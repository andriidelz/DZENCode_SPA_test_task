from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta, date
from django.core.cache import cache
from .models import Event, DailyStats, UserActivity, PopularContent, SearchQuery
import json


class AnalyticsService:
    """
    Service for analytics data collection and analysis
    """
    
    @staticmethod
    def track_event(event_type, content_object=None, user_identifier='', 
                   request=None, **event_data):
        """
        Track an event in the system
        """
        from django.contrib.contenttypes.models import ContentType
        
        # Prepare event data
        event_kwargs = {
            'event_type': event_type,
            'user_identifier': user_identifier,
        }
        
        # Add content object if provided
        if content_object:
            event_kwargs['content_type'] = ContentType.objects.get_for_model(content_object)
            event_kwargs['object_id'] = content_object.id
        
        # Add request metadata if available
        if request:
            event_kwargs['ip_address'] = AnalyticsService._get_client_ip(request)
            event_kwargs['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
            event_kwargs['referer'] = request.META.get('HTTP_REFERER', '')[:200]
        
        # Add custom event data
        if event_data:
            event_kwargs['event_data'] = json.dumps(event_data, default=str)
        
        # Create event
        return Event.objects.create(**event_kwargs)
    
    @staticmethod
    def track_user_activity(user_identifier, ip_address, user_agent, 
                          session_id='', activity_type='page_view'):
        """
        Track user activity and update session
        """
        # Find or create activity session
        activity, created = UserActivity.objects.get_or_create(
            user_identifier=user_identifier,
            ip_address=ip_address,
            session_id=session_id,
            defaults={
                'user_agent': user_agent,
                'session_start': timezone.now(),
                'last_activity': timezone.now()
            }
        )
        
        if not created:
            # Update existing session
            activity.last_activity = timezone.now()
            activity.update_session_duration()
            
            # Update activity counters
            if activity_type == 'page_view':
                activity.pages_visited += 1
            elif activity_type == 'comment':
                activity.comments_posted += 1
            elif activity_type == 'file_upload':
                activity.files_uploaded += 1
            elif activity_type == 'like':
                activity.likes_given += 1
            elif activity_type == 'search':
                activity.searches_performed += 1
            
            activity.save()
        
        return activity
    
    @staticmethod
    def get_daily_stats(date_obj=None):
        """
        Get or create daily statistics for a specific date
        """
        if date_obj is None:
            date_obj = timezone.now().date()
        
        stats, created = DailyStats.objects.get_or_create(
            date=date_obj,
            defaults={
                'comments_created': 0,
                'comments_liked': 0,
                'replies_created': 0,
                'files_uploaded': 0,
                'images_uploaded': 0,
                'text_files_uploaded': 0,
                'new_users': 0,
                'user_logins': 0,
                'page_views': 0,
                'unique_visitors': 0,
                'searches_performed': 0,
                'errors_occurred': 0
            }
        )
        
        return stats
    
    @staticmethod
    def update_daily_stats(date_obj=None):
        """
        Update daily statistics by aggregating events
        """
        if date_obj is None:
            date_obj = timezone.now().date()
        
        # Get events for the date
        start_date = timezone.make_aware(timezone.datetime.combine(date_obj, timezone.datetime.min.time()))
        end_date = start_date + timedelta(days=1)
        
        events = Event.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )
        
        # Aggregate event counts
        event_counts = events.values('event_type').annotate(count=Count('id'))
        counts_dict = {item['event_type']: item['count'] for item in event_counts}
        
        # Update daily stats
        stats = AnalyticsService.get_daily_stats(date_obj)
        
        stats.comments_created = counts_dict.get('comment_created', 0)
        stats.comments_liked = counts_dict.get('comment_liked', 0)
        stats.replies_created = counts_dict.get('comment_replied', 0)
        stats.files_uploaded = counts_dict.get('file_uploaded', 0)
        stats.new_users = counts_dict.get('user_registered', 0)
        stats.user_logins = counts_dict.get('user_login', 0)
        stats.page_views = counts_dict.get('page_view', 0)
        stats.searches_performed = counts_dict.get('search_performed', 0)
        stats.errors_occurred = counts_dict.get('error_occurred', 0)
        
        # Calculate unique visitors
        stats.unique_visitors = events.values('ip_address').distinct().count()
        
        stats.save()
        
        return stats
    
    @staticmethod
    def get_popular_content(content_type='comment', days=7, limit=10):
        """
        Get popular content for a specific time period
        """
        cache_key = f'popular_{content_type}_{days}d_{limit}'
        popular = cache.get(cache_key)
        
        if popular is None:
            start_date = timezone.now().date() - timedelta(days=days)
            
            popular = PopularContent.objects.filter(
                content_type=content_type,
                date__gte=start_date
            ).order_by('-popularity_score')[:limit]
            
            # Cache for 1 hour
            cache.set(cache_key, list(popular), 60 * 60)
        
        return popular
    
    @staticmethod
    def update_popular_content():
        """
        Update popular content scores
        """
        from apps.comments.models import Comment
        from apps.files.models import UploadedFile
        
        today = timezone.now().date()
        
        # Update popular comments
        comments = Comment.objects.filter(is_active=True)
        for comment in comments:
            popular, created = PopularContent.objects.get_or_create(
                content_type='comment',
                content_id=comment.id,
                date=today,
                defaults={
                    'content_title': comment.text[:100],
                    'like_count': comment.likes_count,
                    'comment_count': comment.replies_count
                }
            )
            
            if not created:
                popular.like_count = comment.likes_count
                popular.comment_count = comment.replies_count
            
            popular.calculate_popularity_score()
            popular.save()
        
        # Update popular files
        files = UploadedFile.objects.filter(status='completed')
        for file_obj in files:
            popular, created = PopularContent.objects.get_or_create(
                content_type='file',
                content_id=file_obj.id,
                date=today,
                defaults={
                    'content_title': file_obj.original_name,
                    'view_count': 0  # Would need to track file views
                }
            )
            
            popular.calculate_popularity_score()
            popular.save()
    
    @staticmethod
    def get_analytics_dashboard_data(days=30):
        """
        Get comprehensive analytics data for dashboard
        """
        cache_key = f'analytics_dashboard_{days}d'
        data = cache.get(cache_key)
        
        if data is None:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get daily stats for the period
            daily_stats = DailyStats.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')
            
            # Aggregate totals
            totals = daily_stats.aggregate(
                total_comments=Sum('comments_created'),
                total_likes=Sum('comments_liked'),
                total_files=Sum('files_uploaded'),
                total_users=Sum('new_users'),
                total_page_views=Sum('page_views'),
                total_searches=Sum('searches_performed')
            )
            
            # Get trend data
            trend_data = []
            for stat in daily_stats:
                trend_data.append({
                    'date': stat.date,
                    'comments': stat.comments_created,
                    'likes': stat.comments_liked,
                    'files': stat.files_uploaded,
                    'users': stat.new_users,
                    'page_views': stat.page_views
                })
            
            # Get top search queries
            top_searches = SearchQuery.objects.filter(
                created_at__gte=timezone.make_aware(
                    timezone.datetime.combine(start_date, timezone.datetime.min.time())
                )
            ).values('query').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # Get user activity stats
            active_users = UserActivity.objects.filter(
                session_start__gte=timezone.make_aware(
                    timezone.datetime.combine(start_date, timezone.datetime.min.time())
                )
            ).values('user_identifier').distinct().count()
            
            avg_session_duration = UserActivity.objects.filter(
                session_start__gte=timezone.make_aware(
                    timezone.datetime.combine(start_date, timezone.datetime.min.time())
                )
            ).aggregate(avg_duration=Avg('session_duration'))['avg_duration'] or 0
            
            data = {
                'totals': totals,
                'trend_data': trend_data,
                'top_searches': list(top_searches),
                'active_users': active_users,
                'avg_session_duration': avg_session_duration,
                'popular_comments': AnalyticsService.get_popular_content('comment', days, 5),
                'popular_files': AnalyticsService.get_popular_content('file', days, 5)
            }
            
            # Cache for 30 minutes
            cache.set(cache_key, data, 60 * 30)
        
        return data
    
    @staticmethod
    def track_search_query(query, results_count, response_time, 
                          user_identifier='', ip_address=None):
        """
        Track a search query for analytics
        """
        return SearchQuery.objects.create(
            query=query,
            user_identifier=user_identifier,
            ip_address=ip_address,
            results_count=results_count,
            response_time=response_time
        )
    
    @staticmethod
    def get_search_analytics(days=30):
        """
        Get search analytics data
        """
        start_date = timezone.now() - timedelta(days=days)
        
        queries = SearchQuery.objects.filter(created_at__gte=start_date)
        
        # Top search terms
        top_queries = queries.values('query').annotate(
            count=Count('id'),
            avg_results=Avg('results_count'),
            avg_response_time=Avg('response_time')
        ).order_by('-count')[:20]
        
        # Search trends by day
        search_trends = queries.extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            searches=Count('id'),
            avg_results=Avg('results_count')
        ).order_by('day')
        
        # No results queries
        no_results = queries.filter(results_count=0).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return {
            'top_queries': list(top_queries),
            'search_trends': list(search_trends),
            'no_results_queries': list(no_results),
            'total_searches': queries.count(),
            'avg_results_per_search': queries.aggregate(
                avg=Avg('results_count')
            )['avg'] or 0
        }
    
    @staticmethod
    def _get_client_ip(request):
        """
        Extract client IP from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RealtimeAnalyticsService:
    """
    Service for real-time analytics using MongoDB
    """
    
    def __init__(self):
        from pymongo import MongoClient
        from django.conf import settings
        
        mongo_settings = getattr(settings, 'MONGODB_SETTINGS', {})
        self.client = MongoClient(mongo_settings.get('host', 'mongodb://localhost:27017/'))
        self.db = self.client[mongo_settings.get('db', 'comments_analytics')]
    
    def track_realtime_event(self, event_type, data):
        """
        Track real-time event in MongoDB
        """
        event_doc = {
            'event_type': event_type,
            'data': data,
            'timestamp': timezone.now(),
            'processed': False
        }
        
        return self.db.realtime_events.insert_one(event_doc)
    
    def get_realtime_stats(self, minutes=30):
        """
        Get real-time statistics for the last N minutes
        """
        start_time = timezone.now() - timedelta(minutes=minutes)
        
        pipeline = [
            {
                '$match': {
                    'timestamp': {'$gte': start_time}
                }
            },
            {
                '$group': {
                    '_id': '$event_type',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        results = list(self.db.realtime_events.aggregate(pipeline))
        return {item['_id']: item['count'] for item in results}
    
    def get_active_users_count(self, minutes=15):
        """
        Get count of active users in the last N minutes
        """
        start_time = timezone.now() - timedelta(minutes=minutes)
        
        pipeline = [
            {
                '$match': {
                    'timestamp': {'$gte': start_time},
                    'data.user_identifier': {'$exists': True, '$ne': ''}
                }
            },
            {
                '$group': {
                    '_id': '$data.user_identifier'
                }
            },
            {
                '$count': 'active_users'
            }
        ]
        
        result = list(self.db.realtime_events.aggregate(pipeline))
        return result[0]['active_users'] if result else 0
    
    def cleanup_old_events(self, hours=24):
        """
        Clean up old real-time events
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        result = self.db.realtime_events.delete_many({
            'timestamp': {'$lt': cutoff_time}
        })
        
        return result.deleted_count
