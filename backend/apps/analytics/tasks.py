from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta, date
import logging

logger = logging.getLogger(__name__)


@shared_task
def track_comment_event(comment_id, event_type, parent_id=None, ip_address=None, user_agent=''):
    """
    Track comment-related events asynchronously
    """
    try:
        from apps.comments.models import Comment
        from .services import AnalyticsService
        
        comment = Comment.objects.get(id=comment_id)
        
        # Track the event
        event_data = {
            'comment_id': comment_id,
            'user_name': comment.user_name,
            'text_length': len(comment.text),
        }
        
        if parent_id:
            event_data['parent_id'] = parent_id
        
        if ip_address:
            event_data['ip_address'] = ip_address
        
        if user_agent:
            event_data['user_agent'] = user_agent[:200]
        
        AnalyticsService.track_event(
            event_type=event_type,
            content_object=comment,
            user_identifier=comment.user_name,
            **event_data
        )
        
        # Track user activity
        if ip_address:
            AnalyticsService.track_user_activity(
                user_identifier=comment.user_name,
                ip_address=ip_address,
                user_agent=user_agent,
                activity_type='comment' if event_type == 'comment_created' else 'like'
            )
        
        # Update real-time analytics
        from .services import RealtimeAnalyticsService
        realtime_service = RealtimeAnalyticsService()
        realtime_service.track_realtime_event(event_type, event_data)
        
        logger.info(f"Tracked {event_type} event for comment {comment_id}")
        
    except Exception as e:
        logger.error(f"Failed to track comment event {comment_id}: {e}")
        raise


@shared_task
def track_file_upload_event(file_id, ip_address=None, user_agent=''):
    """
    Track file upload events asynchronously
    """
    try:
        from apps.files.models import UploadedFile
        from .services import AnalyticsService
        
        file_obj = UploadedFile.objects.get(id=file_id)
        
        event_data = {
            'file_id': file_id,
            'file_type': file_obj.file_type,
            'file_size': file_obj.file_size,
            'original_name': file_obj.original_name,
        }
        
        if ip_address:
            event_data['ip_address'] = ip_address
        
        if user_agent:
            event_data['user_agent'] = user_agent[:200]
        
        AnalyticsService.track_event(
            event_type='file_uploaded',
            content_object=file_obj,
            user_identifier=ip_address or 'anonymous',
            **event_data
        )
        
        # Track user activity
        if ip_address:
            AnalyticsService.track_user_activity(
                user_identifier=ip_address,
                ip_address=ip_address,
                user_agent=user_agent,
                activity_type='file_upload'
            )
        
        logger.info(f"Tracked file upload event for file {file_id}")
        
    except Exception as e:
        logger.error(f"Failed to track file upload event {file_id}: {e}")
        raise


@shared_task
def update_daily_analytics():
    """
    Update daily analytics statistics
    """
    try:
        from .services import AnalyticsService
        
        # Update yesterday's stats (to ensure all events are captured)
        yesterday = timezone.now().date() - timedelta(days=1)
        stats = AnalyticsService.update_daily_stats(yesterday)
        
        # Update today's stats
        today_stats = AnalyticsService.update_daily_stats()
        
        logger.info(
            f"Updated daily analytics - Yesterday: {stats.comments_created} comments, "
            f"Today: {today_stats.comments_created} comments"
        )
        
        # Clear analytics cache
        cache.delete_pattern('analytics_*')
        cache.delete_pattern('popular_*')
        
        return {
            'yesterday_comments': stats.comments_created,
            'today_comments': today_stats.comments_created
        }
        
    except Exception as e:
        logger.error(f"Failed to update daily analytics: {e}")
        raise


@shared_task
def update_popular_content():
    """
    Update popular content rankings
    """
    try:
        from .services import AnalyticsService
        
        AnalyticsService.update_popular_content()
        
        # Clear popular content cache
        cache.delete_pattern('popular_*')
        
        logger.info("Updated popular content rankings")
        
    except Exception as e:
        logger.error(f"Failed to update popular content: {e}")
        raise


@shared_task
def cleanup_old_analytics_data():
    """
    Clean up old analytics data
    """
    try:
        from .models import Event, UserActivity, SearchQuery
        from .services import RealtimeAnalyticsService
        
        # Clean up events older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        
        deleted_events = Event.objects.filter(
            created_at__lt=cutoff_date,
            processed=True
        ).delete()[0]
        
        # Clean up user activities older than 60 days
        activity_cutoff = timezone.now() - timedelta(days=60)
        deleted_activities = UserActivity.objects.filter(
            session_start__lt=activity_cutoff
        ).delete()[0]
        
        # Clean up search queries older than 30 days
        search_cutoff = timezone.now() - timedelta(days=30)
        deleted_searches = SearchQuery.objects.filter(
            created_at__lt=search_cutoff
        ).delete()[0]
        
        # Clean up real-time events from MongoDB
        realtime_service = RealtimeAnalyticsService()
        deleted_realtime = realtime_service.cleanup_old_events(hours=24)
        
        logger.info(
            f"Analytics cleanup completed: {deleted_events} events, "
            f"{deleted_activities} activities, {deleted_searches} searches, "
            f"{deleted_realtime} real-time events"
        )
        
        return {
            'deleted_events': deleted_events,
            'deleted_activities': deleted_activities,
            'deleted_searches': deleted_searches,
            'deleted_realtime': deleted_realtime
        }
        
    except Exception as e:
        logger.error(f"Analytics cleanup failed: {e}")
        raise


@shared_task
def generate_analytics_reports():
    """
    Generate and cache analytics reports
    """
    try:
        from .services import AnalyticsService
        
        # Generate dashboard data for different periods
        periods = [7, 30, 90]
        
        for days in periods:
            data = AnalyticsService.get_analytics_dashboard_data(days)
            cache.set(f'analytics_dashboard_{days}d', data, 60 * 60 * 6)  # Cache for 6 hours
        
        # Generate search analytics
        search_data = AnalyticsService.get_search_analytics(30)
        cache.set('search_analytics_30d', search_data, 60 * 60 * 6)
        
        logger.info("Generated analytics reports")
        
    except Exception as e:
        logger.error(f"Failed to generate analytics reports: {e}")
        raise


@shared_task
def track_user_session(user_identifier, ip_address, user_agent, session_id):
    """
    Track user session activity
    """
    try:
        from .services import AnalyticsService
        
        AnalyticsService.track_user_activity(
            user_identifier=user_identifier,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            activity_type='page_view'
        )
        
        logger.debug(f"Tracked session activity for {user_identifier}")
        
    except Exception as e:
        logger.error(f"Failed to track user session: {e}")
        raise


@shared_task
def process_analytics_events():
    """
    Process unprocessed analytics events
    """
    try:
        from .models import Event
        from .services import AnalyticsService
        
        # Get unprocessed events
        unprocessed_events = Event.objects.filter(processed=False)[:1000]
        
        processed_count = 0
        
        for event in unprocessed_events:
            try:
                # Process event based on type
                if event.event_type == 'comment_created':
                    # Update daily stats
                    stats = AnalyticsService.get_daily_stats(event.created_at.date())
                    stats.comments_created += 1
                    stats.save()
                
                elif event.event_type == 'comment_liked':
                    stats = AnalyticsService.get_daily_stats(event.created_at.date())
                    stats.comments_liked += 1
                    stats.save()
                
                elif event.event_type == 'file_uploaded':
                    stats = AnalyticsService.get_daily_stats(event.created_at.date())
                    stats.files_uploaded += 1
                    
                    # Check file type from event data
                    event_data = event.get_event_data()
                    if event_data.get('file_type') == 'image':
                        stats.images_uploaded += 1
                    elif event_data.get('file_type') == 'text':
                        stats.text_files_uploaded += 1
                    
                    stats.save()
                
                # Mark as processed
                event.processed = True
                event.save()
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process event {event.id}: {e}")
        
        logger.info(f"Processed {processed_count} analytics events")
        
        return processed_count
        
    except Exception as e:
        logger.error(f"Failed to process analytics events: {e}")
        raise
