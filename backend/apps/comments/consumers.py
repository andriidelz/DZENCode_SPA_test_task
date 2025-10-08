import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class CommentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time comment updates
    """
    
    async def connect(self):
        # Join comments group
        self.room_group_name = 'comments'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave comments group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': text_data_json.get('timestamp')
            }))
    
    # Receive message from room group
    async def comment_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'comment',
            'data': event['data']
        }, cls=DjangoJSONEncoder))
    
    async def like_message(self, event):
        # Send like update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'like',
            'data': event['data']
        }, cls=DjangoJSONEncoder))
    
    async def reply_message(self, event):
        # Send reply notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'reply',
            'data': event['data']
        }, cls=DjangoJSONEncoder))


def send_comment_notification(comment):
    """
    Send real-time notification when a new comment is created
    """
    channel_layer = get_channel_layer()
    
    if channel_layer:
        from .serializers import CommentListSerializer
        
        serializer = CommentListSerializer(comment)
        
        async_to_sync(channel_layer.group_send)(
            'comments',
            {
                'type': 'comment_message',
                'data': {
                    'action': 'created',
                    'comment': serializer.data
                }
            }
        )


def send_like_notification(comment_like):
    """
    Send real-time notification when a comment is liked
    """
    channel_layer = get_channel_layer()
    
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            'comments',
            {
                'type': 'like_message',
                'data': {
                    'action': 'liked',
                    'comment_id': comment_like.comment.id,
                    'likes_count': comment_like.comment.likes_count
                }
            }
        )


def send_reply_notification(reply_comment):
    """
    Send real-time notification when a reply is created
    """
    channel_layer = get_channel_layer()
    
    if channel_layer:
        from .serializers import CommentListSerializer
        
        serializer = CommentListSerializer(reply_comment)
        
        async_to_sync(channel_layer.group_send)(
            'comments',
            {
                'type': 'reply_message',
                'data': {
                    'action': 'reply_created',
                    'reply': serializer.data,
                    'parent_id': reply_comment.parent.id if reply_comment.parent else None
                }
            }
        )
