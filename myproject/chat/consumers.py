import json
import uuid

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.template.loader import render_to_string
from openai import AsyncOpenAI


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def _set_mode(self, mode: str):
        mode = (mode or "chat").lower()
        if mode not in {"chat", "verb", "word"}:
            await self._send_system(f"Unknown mode: {mode}")
            return
        self.mode = mode
        await self._send_system(f"Mode set to: {mode}")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        mode = text_data_json.get("mode")
        message_text = text_data_json["message"]

        # immediately display user's message
        user_message_html = render_to_string(
            "chat/ws/chat_message.html",
            {
                "message_text": message_text,
                "is_user": True,
            },
        )
        await self.send(text_data=user_message_html)

    

        ###################### Commands handler ######################

        if message_text.lower().strip() == "ping":
            pong_message_html = render_to_string(
                "chat/ws/chat_message.html",
                {
                    "message_text": "pong",
                    "is_system": True,
                },
            )
            await self.send(text_data=pong_message_html)
            return 

        # if message_text.lower().strip().split(' ')[0] == "/mode" & len(message_text.lower().strip().split(' ')) == 2:
        #     print(f"changing mode to {message_text.lower().strip().split(' ')[1] or "verb"}") # debug
        #     await self._set_mode(message_text.lower().strip().split(' ')[1] or "verb")
        #     return 
        

        ##############################################################
        # add user message to chat history
        self.messages.append(
            {
                "role": "user",
                "content": message_text,
            }
        )

        # prepare a placeholder for the bot's response
        message_id = f"message-{uuid.uuid4().hex}"
        bot_response_html = render_to_string(
            "chat/ws/chat_message.html",
            {"is_bot": True, "message_id": message_id},
        )
        await self.send(text_data=bot_response_html)

        # stream response from openai
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        openai_response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.messages,
            stream=True,
            stream_options={"include_usage": True},
        )

        chunks = []
        usage = None
        async for chunk in openai_response:
            if chunk.usage:
                usage = chunk.usage
            
            if chunk.choices and chunk.choices[0].delta.content:
                message_chunk = (chunk.choices[0].delta.content or "")
                formatted_chunk = message_chunk.replace("\n", "<br>")
                # stream the chunk to the placeholder
                await self.send(text_data=f'<div id="{message_id}" hx-swap-oob="beforeend">{formatted_chunk}</div>')
                chunks.append(message_chunk)

        if usage:
            print(f"Total tokens used: {usage.total_tokens}")

        # add the full bot response to the chat history
        self.messages.append({"role": "assistant", "content": "".join(chunks)})
