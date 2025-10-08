import graphene
from graphene_django import DjangoObjectType
from apps.comments.schema import CommentQuery, CommentMutation
from apps.users.schema import UserQuery, UserMutation


class Query(
    CommentQuery,
    UserQuery,
    graphene.ObjectType
):
    pass


class Mutation(
    CommentMutation,
    UserMutation,
    graphene.ObjectType
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
