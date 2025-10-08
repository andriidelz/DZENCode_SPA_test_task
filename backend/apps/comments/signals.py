from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Comment, CommentLike
from apps.analytics.tasks import track_comment_event


@receiver(post_save, sender=Comment)
def comment_post_save(sender, instance, created, **kwargs):
    """
    Handle comment creation and updates
    """
    if created:
        # Clear relevant caches
        cache.delete_many([
            'trending_comments_10',
            'comment_stats',
        ])
        
        # Update parent comment reply count
        if instance.parent:
            instance.parent.replies_count = instance.parent.replies.filter(is_active=True).count()
            instance.parent.save(update_fields=['replies_count'])
        
        # Send to Elasticsearch for indexing
        from .tasks import index_comment_to_elasticsearch
        index_comment_to_elasticsearch.delay(instance.id)
        
        # Send real-time notification via WebSocket
        from .consumers import send_comment_notification
        send_comment_notification(instance)


@receiver(post_delete, sender=Comment)
def comment_post_delete(sender, instance, **kwargs):
    """
    Handle comment deletion
    """
    # Clear caches
    cache.delete_many([
        'trending_comments_10',
        'comment_stats',
    ])
    
    # Update parent comment reply count
    if instance.parent:
        instance.parent.replies_count = instance.parent.replies.filter(is_active=True).count()
        instance.parent.save(update_fields=['replies_count'])
    
    # Remove from Elasticsearch
    from .tasks import remove_comment_from_elasticsearch
    remove_comment_from_elasticsearch.delay(instance.id)


@receiver(post_save, sender=CommentLike)
def comment_like_post_save(sender, instance, created, **kwargs):
    """
    Handle comment like creation
    """
    if created:
        # Update comment likes count
        instance.comment.likes_count = instance.comment.likes.count()
        instance.comment.save(update_fields=['likes_count'])
        
        # Clear trending cache
        cache.delete('trending_comments_10')
        
        # Send real-time notification
        from .consumers import send_like_notification
        send_like_notification(instance)


@receiver(post_delete, sender=CommentLike)
def comment_like_post_delete(sender, instance, **kwargs):
    """
    Handle comment like deletion
    """
    # Update comment likes count
    instance.comment.likes_count = instance.comment.likes.count()
    instance.comment.save(update_fields=['likes_count'])
    
    # Clear trending cache
    cache.delete('trending_comments_10')
