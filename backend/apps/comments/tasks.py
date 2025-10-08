from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def index_comment_to_elasticsearch(comment_id):
    """
    Index a comment to Elasticsearch for search
    """
    try:
        from .models import Comment
        from .documents import CommentDocument
        
        comment = Comment.objects.get(id=comment_id)
        
        # Create or update document in Elasticsearch
        doc = CommentDocument(
            meta={'id': comment.id},
            user_name=comment.user_name,
            text=comment.sanitized_text,
            created_at=comment.created_at,
            likes_count=comment.likes_count,
            replies_count=comment.replies_count,
            is_reply=comment.parent is not None,
            parent_id=comment.parent.id if comment.parent else None
        )
        
        doc.save()
        logger.info(f"Indexed comment {comment_id} to Elasticsearch")
        
    except Exception as e:
        logger.error(f"Failed to index comment {comment_id}: {e}")
        raise


@shared_task
def remove_comment_from_elasticsearch(comment_id):
    """
    Remove a comment from Elasticsearch
    """
    try:
        from .documents import CommentDocument
        
        doc = CommentDocument.get(id=comment_id)
        doc.delete()
        logger.info(f"Removed comment {comment_id} from Elasticsearch")
        
    except Exception as e:
        logger.error(f"Failed to remove comment {comment_id} from Elasticsearch: {e}")


@shared_task
def cleanup_expired_captchas():
    """
    Clean up expired CAPTCHA tokens
    """
    try:
        from .models import CaptchaToken
        
        # Delete CAPTCHAs older than 1 hour
        cutoff_time = timezone.now() - timedelta(hours=1)
        deleted_count = CaptchaToken.objects.filter(
            created_at__lt=cutoff_time
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} expired CAPTCHA tokens")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired CAPTCHAs: {e}")
        raise


@shared_task
def update_comment_statistics():
    """
    Update cached comment statistics
    """
    try:
        from django.db.models import Count, Avg
        from .models import Comment
        
        # Calculate fresh statistics
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        
        stats = {
            'total_comments': Comment.objects.filter(is_active=True).count(),
            'total_replies': Comment.objects.filter(is_active=True, parent__isnull=False).count(),
            'comments_this_week': Comment.objects.filter(
                is_active=True,
                created_at__gte=week_ago
            ).count(),
            'average_replies_per_comment': Comment.objects.filter(
                is_active=True,
                parent__isnull=True
            ).aggregate(avg_replies=Avg('replies_count'))['avg_replies'] or 0,
            'most_liked_comment_id': Comment.objects.filter(
                is_active=True
            ).order_by('-likes_count').values_list('id', flat=True).first(),
            'most_active_users': list(
                Comment.objects.filter(
                    is_active=True
                ).values('user_name').annotate(
                    comment_count=Count('id')
                ).order_by('-comment_count')[:5]
            )
        }
        
        # Cache for 10 minutes
        cache.set('comment_stats', stats, 60 * 10)
        logger.info("Updated comment statistics cache")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to update comment statistics: {e}")
        raise


@shared_task
def detect_and_moderate_spam():
    """
    Detect and automatically moderate spam comments
    """
    try:
        from .models import Comment
        from .services import SpamDetectionService
        
        # Get recent unmoderated comments
        recent_comments = Comment.objects.filter(
            is_active=True,
            is_moderated=False,
            created_at__gte=timezone.now() - timedelta(hours=1)
        )
        
        moderated_count = 0
        
        for comment in recent_comments:
            spam_score = SpamDetectionService.get_spam_score(
                comment.text,
                comment.user_name,
                comment.email,
                comment.ip_address
            )
            
            # Auto-moderate if spam score is high
            if spam_score > 80:
                comment.is_active = False
                comment.is_moderated = True
                comment.moderated_at = timezone.now()
                comment.save()
                moderated_count += 1
                
                logger.info(f"Auto-moderated comment {comment.id} (spam score: {spam_score})")
        
        logger.info(f"Auto-moderated {moderated_count} spam comments")
        return moderated_count
        
    except Exception as e:
        logger.error(f"Failed to detect and moderate spam: {e}")
        raise


@shared_task
def send_comment_notification_email(comment_id):
    """
    Send email notification for new comments (if enabled)
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from .models import Comment
        
        comment = Comment.objects.get(id=comment_id)
        
        if hasattr(settings, 'ADMIN_EMAIL') and settings.ADMIN_EMAIL:
            subject = f"New Comment from {comment.user_name}"
            message = f"""
            New comment posted:
            
            User: {comment.user_name}
            Email: {comment.email}
            Text: {comment.text[:200]}...
            
            View comment: {settings.SITE_URL}/admin/comments/comment/{comment.id}/
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True
            )
            
            logger.info(f"Sent notification email for comment {comment_id}")
    
    except Exception as e:
        logger.error(f"Failed to send notification email for comment {comment_id}: {e}")
