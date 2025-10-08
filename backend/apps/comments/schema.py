import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required
from django.core.exceptions import ValidationError
from .models import Comment, CommentLike, CommentFile
from .serializers import CommentSerializer
from .services import CommentService


class CommentType(DjangoObjectType):
    """
    GraphQL type for Comment model
    """
    depth = graphene.Int()
    can_reply = graphene.Boolean()
    formatted_date = graphene.String()
    
    class Meta:
        model = Comment
        fields = (
            'id', 'user_name', 'home_page', 'sanitized_text', 'parent',
            'created_at', 'updated_at', 'is_active', 'likes_count',
            'replies_count'
        )
        filter_fields = {
            'user_name': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte'],
            'likes_count': ['exact', 'gte', 'lte'],
            'parent': ['exact', 'isnull'],
        }
        interfaces = (graphene.relay.Node,)
    
    def resolve_depth(self, info):
        return self.get_depth()
    
    def resolve_can_reply(self, info):
        return self.can_reply
    
    def resolve_formatted_date(self, info):
        return self.created_at.strftime('%d.%m.%y в %H:%M')


class CommentLikeType(DjangoObjectType):
    """
    GraphQL type for CommentLike model
    """
    class Meta:
        model = CommentLike
        fields = ('id', 'comment', 'created_at')
        interfaces = (graphene.relay.Node,)


class CommentFileType(DjangoObjectType):
    """
    GraphQL type for CommentFile model
    """
    url = graphene.String()
    
    class Meta:
        model = CommentFile
        fields = ('id', 'file_type', 'original_name', 'file_size', 'created_at')
        interfaces = (graphene.relay.Node,)
    
    def resolve_url(self, info):
        request = info.context
        if request and self.file:
            return request.build_absolute_uri(self.file.url)
        return self.file.url if self.file else None


class CreateComment(graphene.Mutation):
    """
    GraphQL mutation to create a new comment
    """
    comment = graphene.Field(CommentType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    class Arguments:
        user_name = graphene.String(required=True)
        email = graphene.String(required=True)
        home_page = graphene.String()
        text = graphene.String(required=True)
        parent_id = graphene.Int()
        captcha_token = graphene.String(required=True)
        captcha_solution = graphene.String(required=True)
    
    def mutate(self, info, user_name, email, text, captcha_token, captcha_solution, home_page=None, parent_id=None):
        try:
            # Prepare data for serializer
            data = {
                'user_name': user_name,
                'email': email,
                'text': text,
                'captcha_token': captcha_token,
                'captcha_solution': captcha_solution
            }
            
            if home_page:
                data['home_page'] = home_page
            
            if parent_id:
                data['parent'] = parent_id
            
            # Use DRF serializer for validation and creation
            serializer = CommentSerializer(data=data, context={'request': info.context})
            
            if serializer.is_valid():
                comment = serializer.save()
                return CreateComment(
                    comment=comment,
                    success=True,
                    errors=[]
                )
            else:
                errors = []
                for field, field_errors in serializer.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                
                return CreateComment(
                    comment=None,
                    success=False,
                    errors=errors
                )
        
        except Exception as e:
            return CreateComment(
                comment=None,
                success=False,
                errors=[str(e)]
            )


class LikeComment(graphene.Mutation):
    """
    GraphQL mutation to like a comment
    """
    comment = graphene.Field(CommentType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    class Arguments:
        comment_id = graphene.Int(required=True)
    
    def mutate(self, info, comment_id):
        try:
            from .serializers import CommentLikeSerializer
            
            data = {'comment': comment_id}
            serializer = CommentLikeSerializer(data=data, context={'request': info.context})
            
            if serializer.is_valid():
                like = serializer.save()
                return LikeComment(
                    comment=like.comment,
                    success=True,
                    errors=[]
                )
            else:
                errors = []
                for field, field_errors in serializer.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                
                return LikeComment(
                    comment=None,
                    success=False,
                    errors=errors
                )
        
        except Exception as e:
            return LikeComment(
                comment=None,
                success=False,
                errors=[str(e)]
            )


class CommentQuery(graphene.ObjectType):
    """
    GraphQL queries for comments
    """
    all_comments = DjangoFilterConnectionField(CommentType)
    comment = graphene.Field(CommentType, id=graphene.Int(required=True))
    trending_comments = graphene.List(CommentType, limit=graphene.Int(default_value=10))
    comment_thread = graphene.List(CommentType, comment_id=graphene.Int(required=True))
    user_comments = graphene.List(
        CommentType,
        user_name=graphene.String(required=True),
        limit=graphene.Int(default_value=50)
    )
    
    def resolve_all_comments(self, info, **kwargs):
        """Get all active top-level comments"""
        return Comment.objects.filter(is_active=True, parent__isnull=True).order_by('-created_at')
    
    def resolve_comment(self, info, id):
        """Get a specific comment by ID"""
        try:
            return Comment.objects.get(id=id, is_active=True)
        except Comment.DoesNotExist:
            return None
    
    def resolve_trending_comments(self, info, limit=10):
        """Get trending comments"""
        return CommentService.get_trending_comments(limit=limit)
    
    def resolve_comment_thread(self, info, comment_id):
        """Get full comment thread"""
        return CommentService.get_comment_thread(comment_id)
    
    def resolve_user_comments(self, info, user_name, limit=50):
        """Get comments by specific user"""
        return CommentService.get_user_comment_history(user_name, limit=limit)


class CommentMutation(graphene.ObjectType):
    """
    GraphQL mutations for comments
    """
    create_comment = CreateComment.Field()
    like_comment = LikeComment.Field()
