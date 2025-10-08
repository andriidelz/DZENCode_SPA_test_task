from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Comment


@registry.register_document
class CommentDocument(Document):
    """
    Elasticsearch document for comments search
    """
    
    # User information
    user_name = fields.TextField(
        analyzer='standard',
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField()
        }
    )
    
    # Comment content
    text = fields.TextField(
        analyzer='standard',
        fields={
            'raw': fields.KeywordField()
        }
    )
    
    sanitized_text = fields.TextField(
        analyzer='standard'
    )
    
    # Hierarchical information
    is_reply = fields.BooleanField()
    parent_id = fields.IntegerField()
    
    # Metadata
    created_at = fields.DateField()
    likes_count = fields.IntegerField()
    replies_count = fields.IntegerField()
    
    # Search boost fields
    text_length = fields.IntegerField()
    engagement_score = fields.FloatField()
    
    class Index:
        name = 'comments'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'comment_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': [
                            'lowercase',
                            'asciifolding',
                            'stop',
                            'snowball'
                        ]
                    }
                }
            }
        }
    
    class Django:
        model = Comment
        fields = [
            'id',
        ]
        related_models = [Comment]
    
    def get_queryset(self):
        """Return the queryset that should be indexed by this doc type."""
        return super().get_queryset().filter(is_active=True)
    
    def prepare_text_length(self, instance):
        """Calculate text length for scoring"""
        return len(instance.sanitized_text)
    
    def prepare_engagement_score(self, instance):
        """Calculate engagement score based on likes and replies"""
        return (instance.likes_count * 2) + instance.replies_count
    
    def prepare_is_reply(self, instance):
        """Check if this is a reply to another comment"""
        return instance.parent is not None
    
    def prepare_parent_id(self, instance):
        """Get parent comment ID"""
        return instance.parent.id if instance.parent else None


class CommentSearchService:
    """
    Service for searching comments using Elasticsearch
    """
    
    @staticmethod
    def search_comments(query, filters=None, sort_by='_score', page=1, page_size=25):
        """
        Search comments with advanced filtering and sorting
        """
        from elasticsearch_dsl import Search, Q
        from django.conf import settings
        
        # Create search object
        search = Search(index='comments')
        
        if query:
            # Multi-field search with boosting
            search_query = Q('multi_match', 
                query=query,
                fields=[
                    'text^3',           # Boost text content
                    'sanitized_text^2', # Boost sanitized text
                    'user_name^1.5',    # Boost username
                ],
                type='best_fields',
                fuzziness='AUTO'
            )
            
            # Add highlight
            search = search.query(search_query).highlight(
                'text',
                'sanitized_text',
                fragment_size=150,
                number_of_fragments=3
            )
        else:
            search = search.query('match_all')
        
        # Apply filters
        if filters:
            if 'user_name' in filters:
                search = search.filter('term', user_name__raw=filters['user_name'])
            
            if 'is_reply' in filters:
                search = search.filter('term', is_reply=filters['is_reply'])
            
            if 'min_likes' in filters:
                search = search.filter('range', likes_count={'gte': filters['min_likes']})
            
            if 'date_from' in filters:
                search = search.filter('range', created_at={'gte': filters['date_from']})
            
            if 'date_to' in filters:
                search = search.filter('range', created_at={'lte': filters['date_to']})
        
        # Apply sorting
        if sort_by == 'date_desc':
            search = search.sort('-created_at')
        elif sort_by == 'date_asc':
            search = search.sort('created_at')
        elif sort_by == 'likes_desc':
            search = search.sort('-likes_count')
        elif sort_by == 'engagement':
            search = search.sort('-engagement_score')
        elif sort_by == 'relevance':
            # Default relevance sorting
            pass
        
        # Apply pagination
        start = (page - 1) * page_size
        search = search[start:start + page_size]
        
        # Execute search
        response = search.execute()
        
        # Process results
        results = []
        for hit in response:
            result = {
                'id': hit.meta.id,
                'score': hit.meta.score,
                'user_name': hit.user_name,
                'text': hit.sanitized_text,
                'created_at': hit.created_at,
                'likes_count': hit.likes_count,
                'replies_count': hit.replies_count,
                'is_reply': hit.is_reply,
                'parent_id': hit.parent_id,
            }
            
            # Add highlights if available
            if hasattr(hit.meta, 'highlight'):
                result['highlights'] = dict(hit.meta.highlight)
            
            results.append(result)
        
        return {
            'results': results,
            'total': response.hits.total.value,
            'took': response.took,
            'max_score': response.hits.max_score
        }
    
    @staticmethod
    def suggest_users(query, limit=10):
        """
        Get user name suggestions based on partial input
        """
        from elasticsearch_dsl import Search
        
        search = Search(index='comments')
        search = search.suggest(
            'user_suggestions',
            query,
            completion={
                'field': 'user_name.suggest',
                'size': limit,
                'skip_duplicates': True
            }
        )
        
        response = search.execute()
        suggestions = []
        
        if 'user_suggestions' in response.suggest:
            for option in response.suggest.user_suggestions[0].options:
                suggestions.append(option._source.user_name)
        
        return list(set(suggestions))  # Remove duplicates
    
    @staticmethod
    def get_popular_searches(limit=10):
        """
        Get popular search terms (would require search query logging)
        """
        # This would require implementing search query logging
        # For now, return some common terms
        return [
            'bug', 'feature', 'question', 'help', 'issue',
            'suggestion', 'feedback', 'improvement', 'problem', 'solution'
        ]
