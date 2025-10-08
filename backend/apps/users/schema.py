import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
from .models import User, UserPreference
from .serializers import UserRegistrationSerializer


class UserType(DjangoObjectType):
    """
    GraphQL type for User model
    """
    avatar_url = graphene.String()
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'bio', 'website', 'comments_count', 'likes_received',
            'date_joined', 'last_login', 'show_email'
        )
        interfaces = (graphene.relay.Node,)
    
    def resolve_avatar_url(self, info):
        if self.avatar:
            request = info.context
            if request:
                return request.build_absolute_uri(self.avatar.url)
            return self.avatar.url
        return None


class UserPreferenceType(DjangoObjectType):
    """
    GraphQL type for UserPreference model
    """
    class Meta:
        model = UserPreference
        fields = (
            'theme', 'language', 'comments_per_page',
            'email_on_reply', 'email_on_like', 'email_digest'
        )
        interfaces = (graphene.relay.Node,)


class RegisterUser(graphene.Mutation):
    """
    GraphQL mutation for user registration
    """
    user = graphene.Field(UserType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        password_confirm = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()
        bio = graphene.String()
        website = graphene.String()
    
    def mutate(self, info, username, email, password, password_confirm, **kwargs):
        try:
            data = {
                'username': username,
                'email': email,
                'password': password,
                'password_confirm': password_confirm,
                **kwargs
            }
            
            serializer = UserRegistrationSerializer(data=data)
            if serializer.is_valid():
                user = serializer.save()
                return RegisterUser(
                    user=user,
                    success=True,
                    errors=[]
                )
            else:
                errors = []
                for field, field_errors in serializer.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                
                return RegisterUser(
                    user=None,
                    success=False,
                    errors=errors
                )
        
        except Exception as e:
            return RegisterUser(
                user=None,
                success=False,
                errors=[str(e)]
            )


class UpdateUserProfile(graphene.Mutation):
    """
    GraphQL mutation for updating user profile
    """
    user = graphene.Field(UserType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    
    class Arguments:
        first_name = graphene.String()
        last_name = graphene.String()
        bio = graphene.String()
        website = graphene.String()
        show_email = graphene.Boolean()
    
    @login_required
    def mutate(self, info, **kwargs):
        try:
            user = info.context.user
            
            for field, value in kwargs.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            user.save()
            
            return UpdateUserProfile(
                user=user,
                success=True,
                errors=[]
            )
        
        except Exception as e:
            return UpdateUserProfile(
                user=None,
                success=False,
                errors=[str(e)]
            )


class UserQuery(graphene.ObjectType):
    """
    GraphQL queries for users
    """
    me = graphene.Field(UserType)
    user = graphene.Field(UserType, username=graphene.String(required=True))
    users = graphene.List(UserType, search=graphene.String())
    
    @login_required
    def resolve_me(self, info):
        """Get current authenticated user"""
        return info.context.user
    
    def resolve_user(self, info, username):
        """Get user by username"""
        try:
            return User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return None
    
    def resolve_users(self, info, search=None):
        """Search users"""
        if search:
            from .services import UserService
            return UserService.search_users(search)
        return User.objects.filter(is_active=True).order_by('username')[:20]


class UserMutation(graphene.ObjectType):
    """
    GraphQL mutations for users
    """
    register_user = RegisterUser.Field()
    update_profile = UpdateUserProfile.Field()
