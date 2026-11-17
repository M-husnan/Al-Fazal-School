import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id=self.scope['url_route']['kwargs']['room_id']
        user=self.scope.get('user')
        if not user or not user.is_authenticated or not await self.is_member(user.id):
            await self.close(code=4401); return
        self.group_name=f'school_chat_{self.room_id}'
        await self.channel_layer.group_add(self.group_name,self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(self.group_name,{'type':'chat.presence','user_id':user.id,'online':True})
    async def disconnect(self,close_code):
        if hasattr(self,'group_name'):
            user=self.scope.get('user')
            if user and user.is_authenticated:
                await self.channel_layer.group_send(self.group_name,{'type':'chat.presence','user_id':user.id,'online':False})
            await self.channel_layer.group_discard(self.group_name,self.channel_name)
    async def receive_json(self,content,**kwargs):
        # Persistent message bodies and file uploads go through authenticated REST endpoints.
        # WebSocket events are for typing, live delivery, read receipts, and presence.
        if content.get('type') in ('typing','seen'):
            await self.channel_layer.group_send(self.group_name,{'type':'chat.event','event':content,'sender_id':self.scope['user'].id})
    async def chat_message(self,event):
        await self.send_json({'type':'message','message':event['message']})
    async def chat_event(self,event):
        if event.get('sender_id')!=self.scope['user'].id: await self.send_json({'type':'event','event':event['event'],'sender_id':event.get('sender_id')})
    async def chat_presence(self,event):
        if event.get('user_id')!=self.scope['user'].id: await self.send_json({'type':'presence','user_id':event['user_id'],'online':event['online']})
    @database_sync_to_async
    def is_member(self,user_id): return ChatRoom.objects.filter(pk=self.room_id,members__id=user_id).exists()
