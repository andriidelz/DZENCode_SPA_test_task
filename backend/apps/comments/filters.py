import django_filters
from django.db import models
from .models import Comment


class CommentFilter(django_filters.FilterSet):
    """
    Filter class for comments with various filtering options
    """
    user_name = django_filters.CharFilter(
        field_name='user_name',
        lookup_expr='icontains',
        help_text="Filter by username (case-insensitive)"
    )
    
    email = django_filters.CharFilter(
        field_name='email',
        lookup_expr='iexact',
        help_text="Filter by exact email"
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter comments created after this date"
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter comments created before this date"
    )
    
    date_range = django_filters.DateFromToRangeFilter(
        field_name='created_at',
        help_text="Filter comments within date range"
    )
    
    has_replies = django_filters.BooleanFilter(
        method='filter_has_replies',
        help_text="Filter comments that have replies"
    )
    
    min_likes = django_filters.NumberFilter(
        field_name='likes_count',
        lookup_expr='gte',
        help_text="Filter comments with minimum number of likes"
    )
    
    has_files = django_filters.BooleanFilter(
        method='filter_has_files',
        help_text="Filter comments that have file attachments"
    )
    
    text_contains = django_filters.CharFilter(
        field_name='sanitized_text',
        lookup_expr='icontains',
        help_text="Filter by text content (case-insensitive)"
    )
    
    class Meta:
        model = Comment
        fields = {
            'user_name': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte'],
            'likes_count': ['exact', 'gte', 'lte'],
            'replies_count': ['exact', 'gte', 'lte'],
        }
    
    def filter_has_replies(self, queryset, name, value):
        """Filter comments that have/don't have replies"""
        if value:
            return queryset.filter(replies_count__gt=0)
        else:
            return queryset.filter(replies_count=0)
    
    def filter_has_files(self, queryset, name, value):
        """Filter comments that have/don't have file attachments"""
        if value:
            return queryset.filter(files__isnull=False).distinct()
        else:
            return queryset.filter(files__isnull=True)
