from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import random
import string
import math

from analytics import models


class CommentService:
    """
    Service class for comment-related business logic
    """
    
    @staticmethod
    def get_trending_comments(limit=10):
        """
        Get trending comments based on likes and recent activity
        """
        cache_key = f'trending_comments_{limit}'
        trending = cache.get(cache_key)
        
        if trending is None:
            from .models import Comment
            from datetime import timedelta
            
            # Get comments from last 7 days with high engagement
            week_ago = timezone.now() - timedelta(days=7)
            
            trending = Comment.objects.filter(
                is_active=True,
                created_at__gte=week_ago
            ).order_by(
                '-likes_count',
                '-replies_count',
                '-created_at'
            )[:limit]
            
            # Cache for 1 hour
            cache.set(cache_key, list(trending), 60 * 60)
        
        return trending
    
    @staticmethod
    def get_user_comment_history(user_name, limit=50):
        """
        Get comment history for a specific user
        """
        from .models import Comment
        
        return Comment.objects.filter(
            user_name__iexact=user_name,
            is_active=True
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_comment_thread(comment_id):
        """
        Get full comment thread (root comment + all nested replies)
        """
        from .models import Comment
        
        try:
            comment = Comment.objects.get(id=comment_id, is_active=True)
            
            # If this is a reply, get the root comment
            root_comment = comment
            while root_comment.parent:
                root_comment = root_comment.parent
            
            # Get all comments in this thread
            thread_comments = Comment.objects.filter(
                models.Q(id=root_comment.id) |
                models.Q(parent=root_comment) |
                models.Q(parent__parent=root_comment) |
                models.Q(parent__parent__parent=root_comment)
            ).filter(
                is_active=True
            ).select_related('parent').order_by('created_at')
            
            return thread_comments
        except Comment.DoesNotExist:
            return Comment.objects.none()
    
    @staticmethod
    def mark_comment_as_spam(comment_id, moderator_user=None):
        """
        Mark a comment as spam and hide it
        """
        from .models import Comment
        
        try:
            comment = Comment.objects.get(id=comment_id)
            comment.is_active = False
            comment.is_moderated = True
            comment.moderated_by = moderator_user
            comment.moderated_at = timezone.now()
            comment.save()
            
            # Clear relevant caches
            cache.delete_many([
                'trending_comments_10',
                'comment_stats',
            ])
            
            return True
        except Comment.DoesNotExist:
            return False


class CaptchaService:
    """
    Service for generating CAPTCHA images
    """
    
    def __init__(self):
        self.width = getattr(settings, 'CAPTCHA_IMAGE_SIZE', (120, 50))[0]
        self.height = getattr(settings, 'CAPTCHA_IMAGE_SIZE', (120, 50))[1]
        self.font_size = getattr(settings, 'CAPTCHA_FONT_SIZE', 24)
        self.bg_color = getattr(settings, 'CAPTCHA_BACKGROUND_COLOR', '#ffffff')
        self.fg_color = getattr(settings, 'CAPTCHA_FOREGROUND_COLOR', '#000000')
    
    def generate_image(self, challenge_text):
        """
        Generate CAPTCHA image for the given challenge text
        """
        # Create image
        image = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fallback to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", self.font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Get text size
        if font:
            bbox = draw.textbbox((0, 0), challenge_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = len(challenge_text) * 10
            text_height = 20
        
        # Center the text
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2
        
        # Add some noise lines
        for _ in range(5):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill='#cccccc', width=1)
        
        # Draw text with slight rotation and distortion
        for i, char in enumerate(challenge_text):
            char_x = x + i * (text_width // len(challenge_text))
            char_y = y + random.randint(-5, 5)
            
            # Add slight color variation
            color_variation = random.randint(-30, 30)
            if self.fg_color == '#000000':
                char_color = f"#{max(0, color_variation):02x}{max(0, color_variation):02x}{max(0, color_variation):02x}"
            else:
                char_color = self.fg_color
            
            draw.text((char_x, char_y), char, fill=char_color, font=font)
        
        # Add some noise dots
        for _ in range(20):
            x_dot = random.randint(0, self.width)
            y_dot = random.randint(0, self.height)
            draw.point((x_dot, y_dot), fill='#999999')
        
        # Save to bytes
        img_buffer = BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    
    def generate_math_challenge(self):
        """
        Generate a simple math challenge
        """
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operation = random.choice(['+', '-'])
        
        if operation == '+':
            challenge = f"{num1} + {num2} = ?"
            solution = str(num1 + num2)
        else:
            # Make sure result is positive
            if num1 < num2:
                num1, num2 = num2, num1
            challenge = f"{num1} - {num2} = ?"
            solution = str(num1 - num2)
        
        return challenge, solution


class SpamDetectionService:
    """
    Service for detecting spam comments
    """
    
    @staticmethod
    def is_spam(comment_text, user_name, email, ip_address):
        """
        Simple spam detection based on common patterns
        """
        spam_indicators = 0
        
        # Check for common spam keywords
        spam_keywords = [
            'casino', 'poker', 'viagra', 'cialis', 'lottery', 'winner',
            'click here', 'free money', 'make money', 'work from home',
            'buy now', 'limited time', 'act now', 'congratulations'
        ]
        
        text_lower = comment_text.lower()
        for keyword in spam_keywords:
            if keyword in text_lower:
                spam_indicators += 1
        
        # Check for excessive caps
        if len([c for c in comment_text if c.isupper()]) > len(comment_text) * 0.7:
            spam_indicators += 1
        
        # Check for excessive links
        if comment_text.count('http') > 2:
            spam_indicators += 2
        
        # Check for repeated characters
        if any(char * 5 in comment_text for char in 'abcdefghijklmnopqrstuvwxyz'):
            spam_indicators += 1
        
        # Check recent submission frequency from same IP
        from .models import Comment
        from datetime import timedelta
        
        recent_comments = Comment.objects.filter(
            ip_address=ip_address,
            created_at__gte=timezone.now() - timedelta(minutes=10)
        ).count()
        
        if recent_comments > 3:
            spam_indicators += 2
        
        # Return True if spam score is high
        return spam_indicators >= 3
    
    @staticmethod
    def get_spam_score(comment_text, user_name, email, ip_address):
        """
        Get spam score for a comment (0-100)
        """
        # This is a simplified version
        # In production, you might use ML models or external APIs
        
        score = 0
        
        # Basic checks similar to is_spam but with weighted scores
        spam_keywords = [
            'casino', 'poker', 'viagra', 'cialis', 'lottery', 'winner',
            'click here', 'free money', 'make money', 'work from home'
        ]
        
        text_lower = comment_text.lower()
        keyword_count = sum(1 for keyword in spam_keywords if keyword in text_lower)
        score += keyword_count * 15
        
        # URL count
        url_count = comment_text.count('http')
        score += url_count * 10
        
        # Caps ratio
        caps_ratio = len([c for c in comment_text if c.isupper()]) / max(len(comment_text), 1)
        score += caps_ratio * 30
        
        # Length check (very short or very long can be suspicious)
        if len(comment_text) < 10 or len(comment_text) > 2000:
            score += 10
        
        return min(score, 100)
