from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache


class UserService:
    """
    Service class for user-related business logic
    """
    
    @staticmethod
    def get_user_stats(user):
        """
        Get comprehensive statistics for a user
        """
        cache_key = f'user_stats_{user.id}'
        stats = cache.get(cache_key)
        
        if stats is None:
            from apps.comments.models import Comment, CommentLike
            
            # Get user's comments
            user_comments = Comment.objects.filter(
                user_name=user.username,
                is_active=True
            )
            
            # Calculate statistics
            total_comments = user_comments.count()
            
            # Get likes received on user's comments
            total_likes_received = CommentLike.objects.filter(
                comment__user_name=user.username,
                comment__is_active=True
            ).count()
            
            # Get replies received
            total_replies_received = Comment.objects.filter(
                parent__user_name=user.username,
                parent__is_active=True,
                is_active=True
            ).count()
            
            # Get most liked comment
            most_liked_comment = user_comments.order_by('-likes_count').first()
            most_liked_data = None
            if most_liked_comment:
                most_liked_data = {
                    'id': most_liked_comment.id,
                    'text': most_liked_comment.sanitized_text[:100],
                    'likes_count': most_liked_comment.likes_count,
                    'created_at': most_liked_comment.created_at
                }
            
            # Get recent activity
            recent_activity = UserService.get_user_activity(user, limit=10)
            
            stats = {
                'total_comments': total_comments,
                'total_likes_received': total_likes_received,
                'total_replies_received': total_replies_received,
                'most_liked_comment': most_liked_data,
                'recent_activity': recent_activity,
                'join_date': user.date_joined,
                'last_comment_date': user.last_comment_at
            }
            
            # Cache for 1 hour
            cache.set(cache_key, stats, 60 * 60)
        
        return stats
    
    @staticmethod
    def get_user_activity(user, limit=20):
        """
        Get recent activity for a user
        """
        from apps.comments.models import Comment, CommentLike
        
        activities = []
        
        # Get recent comments
        recent_comments = Comment.objects.filter(
            user_name=user.username,
            is_active=True
        ).order_by('-created_at')[:limit//2]
        
        for comment in recent_comments:
            activities.append({
                'type': 'comment',
                'action': 'posted',
                'target_id': comment.id,
                'target_text': comment.sanitized_text[:100],
                'created_at': comment.created_at,
                'parent_id': comment.parent.id if comment.parent else None
            })
        
        # Get recent likes received
        recent_likes = CommentLike.objects.filter(
            comment__user_name=user.username,
            comment__is_active=True
        ).order_by('-created_at')[:limit//2]
        
        for like in recent_likes:
            activities.append({
                'type': 'like',
                'action': 'received',
                'target_id': like.comment.id,
                'target_text': like.comment.sanitized_text[:100],
                'created_at': like.created_at
            })
        
        # Sort by date and limit
        activities.sort(key=lambda x: x['created_at'], reverse=True)
        return activities[:limit]
    
    @staticmethod
    def update_user_stats(user):
        """
        Update cached user statistics
        """
        from apps.comments.models import Comment, CommentLike
        
        # Update comment count
        comments_count = Comment.objects.filter(
            user_name=user.username,
            is_active=True
        ).count()
        
        # Update likes received count
        likes_received = CommentLike.objects.filter(
            comment__user_name=user.username,
            comment__is_active=True
        ).count()
        
        # Update last comment date
        last_comment = Comment.objects.filter(
            user_name=user.username,
            is_active=True
        ).order_by('-created_at').first()
        
        last_comment_at = last_comment.created_at if last_comment else None
        
        # Update user model
        user.comments_count = comments_count
        user.likes_received = likes_received
        user.last_comment_at = last_comment_at
        user.save(update_fields=['comments_count', 'likes_received', 'last_comment_at'])
        
        # Clear cached stats
        cache.delete(f'user_stats_{user.id}')
    
    @staticmethod
    def get_top_users(limit=10, period='all_time'):
        """
        Get top users by various metrics
        """
        from apps.comments.models import Comment
        
        cache_key = f'top_users_{period}_{limit}'
        top_users = cache.get(cache_key)
        
        if top_users is None:
            # Calculate date filter based on period
            date_filter = Q()
            if period == 'week':
                week_ago = timezone.now() - timedelta(days=7)
                date_filter = Q(created_at__gte=week_ago)
            elif period == 'month':
                month_ago = timezone.now() - timedelta(days=30)
                date_filter = Q(created_at__gte=month_ago)
            
            # Get users with most comments in period
            top_users = Comment.objects.filter(
                is_active=True
            ).filter(date_filter).values(
                'user_name'
            ).annotate(
                comment_count=Count('id'),
                total_likes=Sum('likes_count')
            ).order_by('-comment_count', '-total_likes')[:limit]
            
            # Convert to list for JSON serialization
            top_users = list(top_users)
            
            # Cache for 1 hour
            cache.set(cache_key, top_users, 60 * 60)
        
        return top_users
    
    @staticmethod
    def get_user_engagement_score(user):
        """
        Calculate user engagement score based on various factors
        """
        from apps.comments.models import Comment, CommentLike
        
        # Base metrics
        comments_count = Comment.objects.filter(
            user_name=user.username,
            is_active=True
        ).count()
        
        likes_received = CommentLike.objects.filter(
            comment__user_name=user.username,
            comment__is_active=True
        ).count()
        
        replies_received = Comment.objects.filter(
            parent__user_name=user.username,
            parent__is_active=True,
            is_active=True
        ).count()
        
        # Calculate score (weighted)
        score = (
            comments_count * 1.0 +      # Base points for comments
            likes_received * 2.0 +     # More points for likes
            replies_received * 1.5     # Points for generating discussion
        )
        
        # Account age bonus (older accounts get slight bonus)
        account_age_days = (timezone.now() - user.date_joined).days
        if account_age_days > 365:
            score *= 1.1
        elif account_age_days > 30:
            score *= 1.05
        
        return round(score, 2)
    
    @staticmethod
    def search_users(query, limit=20):
        """
        Search users by username, first name, or last name
        """
        from django.db.models import Q
        from .models import User
        
        if not query:
            return User.objects.none()
        
        return User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).filter(
            is_active=True
        ).order_by('username')[:limit]
