import json
import uuid

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.template.loader import render_to_string
from openai import AsyncOpenAI
from channels.db import database_sync_to_async
from verbs.models import Verb
from verbs.services import TrainingEngine, preselect_verbs


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        # Chat modes: chat (default), verb, word
        self.mode = "chat"
        self.verb_state = {
            "direction": "es_fr",  # es -> fr by default
            "awaiting": False,
            "current_id": None,
            "attempts": 0,
            # session data
            "queue": [],
            "idx": 0,
            "total": 0,
            "correct": 0,
        }
        await self.accept()

    # --- Helpers ---
    async def _send_system(self, text: str):
        html = render_to_string(
            "chat/ws/chat_message.html",
            {"message_text": text, "is_system": True},
        )
        await self.send(text_data=html)

    async def _oob_replace_message_list(self, inner_html: str):
        await self.send(text_data=f'<div id="message-list" hx-swap-oob="innerHTML">{inner_html}</div>')

    async def _set_mode(self, mode: str):
        mode = (mode or "chat").lower()
        if mode not in {"chat", "verb", "word"}:
            await self._send_system(f"Unknown mode: {mode}")
            return
        self.mode = mode
        await self._send_system(f"Mode set to: {mode}")
        if mode == "verb":
            await self._verb_show_menu()

    # ===== Verb Mode =====
    async def _verb_show_menu(self):
        html = render_to_string(
            "chat/ws/verb_menu.html",
            {
                "direction": self.verb_state["direction"],
                "sizes": [5, 10, 20],
                "selected_size": max(self.verb_state.get("total", 0) or 10, 10),
            },
        )
        await self._oob_replace_message_list(html)

    async def _verb_pick_next(self):
        user = self.scope.get("user")

        @database_sync_to_async
        def _pick_id_sync():
            if getattr(user, "is_authenticated", False):
                ids = preselect_verbs(user, 1)
                if ids:
                    return ids[0]
            v = Verb.objects.order_by('id').first()
            return v.id if v else None

        return await _pick_id_sync()

    async def _verb_get_prompt_and_answer(self, vid: int):
        user = self.scope.get("user")

        @database_sync_to_async
        def _sync():
            engine = TrainingEngine(user, self.verb_state["direction"])  # type: ignore
            verb = Verb.objects.get(id=vid)
            prompt, correct = engine.format_prompt_answer(verb)
            return prompt, correct

        return await _sync()

    async def _verb_render_practice(self, feedback: str | None = None, hint: str | None = None, reveal: str | None = None):
        if not self.verb_state["queue"] or self.verb_state["idx"] >= self.verb_state["total"]:
            # session over
            html = render_to_string(
                "chat/ws/verb_menu.html",
                {
                    "direction": self.verb_state["direction"],
                    "sizes": [5, 10, 20],
                    "selected_size": 10,
                    "complete": True,
                    "correct": self.verb_state.get("correct", 0),
                    "total": self.verb_state.get("total", 0),
                },
            )
            await self._oob_replace_message_list(html)
            return
        vid = self.verb_state["queue"][self.verb_state["idx"]]
        prompt, correct_text = await self._verb_get_prompt_and_answer(vid)
        label = "Translate to French" if self.verb_state["direction"] == "es_fr" else "Translate to Spanish"
        html = render_to_string(
            "chat/ws/verb_practice.html",
            {
                "label": label,
                "prompt": prompt,
                "progress": f"{self.verb_state['idx']+1}/{self.verb_state['total']} (✅ {self.verb_state['correct']})",
                "feedback": feedback,
                "hint": hint,
                "reveal": reveal,
            },
        )
        await self._oob_replace_message_list(html)

    async def _verb_start_session(self, size: int):
        user = self.scope.get("user")

        @database_sync_to_async
        def _build_queue():
            if getattr(user, "is_authenticated", False):
                ids = preselect_verbs(user, size) or []
            else:
                ids = list(Verb.objects.order_by('id').values_list('id', flat=True)[:size])
            return list(ids)

        queue = await _build_queue()
        if not queue:
            await self._send_system("No verbs available to train.")
            return
        self.verb_state.update({
            "queue": queue,
            "idx": 0,
            "total": len(queue),
            "correct": 0,
            "attempts": 0,
        })
        await self._verb_render_practice()

    async def _verb_handle_answer(self, answer: str):
        if not self.verb_state["queue"]:
            await self._verb_show_menu()
            return
        vid = self.verb_state["queue"][self.verb_state["idx"]]
        _, correct_text = await self._verb_get_prompt_and_answer(vid)
        user = self.scope.get("user")

        @database_sync_to_async
        def _check_sync():
            engine = TrainingEngine(user, self.verb_state["direction"])  # type: ignore
            return engine.is_correct(correct_text, answer)

        is_ok = await _check_sync()

        @database_sync_to_async
        def _update_sync():
            engine = TrainingEngine(user, self.verb_state["direction"])  # type: ignore
            engine.update_on_result(vid, is_ok)

        await _update_sync()
        if is_ok:
            self.verb_state["correct"] += 1
            self.verb_state["idx"] += 1
            self.verb_state["attempts"] = 0
            await self._verb_render_practice(feedback="✅ Correct!")
        else:
            self.verb_state["attempts"] += 1
            level = min(self.verb_state["attempts"], 3)

            @database_sync_to_async
            def _hint_sync():
                engine = TrainingEngine(user, self.verb_state["direction"])  # type: ignore
                return engine.hint(correct_text, level)

            hint = await _hint_sync()
            await self._verb_render_practice(feedback="❌ Not quite.", hint=hint)

    async def _verb_give_up(self):
        if not self.verb_state["queue"]:
            await self._verb_show_menu()
            return
        vid = self.verb_state["queue"][self.verb_state["idx"]]
        _, correct_text = await self._verb_get_prompt_and_answer(vid)
        self.verb_state["idx"] += 1
        self.verb_state["attempts"] = 0
        await self._verb_render_practice(reveal=correct_text)

    # ===== Receive =====
    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data.get("command")
        mode = data.get("mode")
        message_text: str = data.get("message", "")
        trimmed = (message_text or "").strip()

        # Commands first
        if command == "set_mode":
            await self._set_mode(mode or "chat")
            return
        if command == "verb_menu":
            await self._verb_show_menu()
            return
        if command == "verb_set_direction":
            new_dir = (data.get("direction") or self.verb_state["direction"]).lower()
            if new_dir in {"es_fr", "fr_es"}:
                self.verb_state["direction"] = new_dir
            await self._verb_show_menu()
            return
        if command == "verb_start":
            try:
                size = int(data.get("size") or 10)
            except Exception:
                size = 10
            await self._verb_start_session(size)
            return
        if command == "verb_hint":
            # re-render with a stronger hint without consuming the item
            if self.verb_state["queue"]:
                vid = self.verb_state["queue"][self.verb_state["idx"]]
                _, correct_text = await self._verb_get_prompt_and_answer(vid)
                user = self.scope.get("user")

                @database_sync_to_async
                def _hint_sync():
                    engine = TrainingEngine(user, self.verb_state["direction"])  # type: ignore
                    return engine.hint(correct_text, min(self.verb_state["attempts"] + 1, 3))

                hint = await _hint_sync()
                await self._verb_render_practice(hint=hint)
            return
        if command == "verb_give_up":
            await self._verb_give_up()
            return
        if command == "verb_back":
            # reset session but keep direction
            self.verb_state.update({"queue": [], "idx": 0, "total": 0, "correct": 0, "attempts": 0})
            await self._verb_show_menu()
            return

        # Ignore empty messages entirely in verb mode
        if self.mode == "verb":
            if trimmed:
                await self._verb_handle_answer(trimmed)
            return

        # Ignore empty messages
        if not trimmed:
            return

        # immediately display user's message (chat mode only)
        user_message_html = render_to_string(
            "chat/ws/chat_message.html",
            {"message_text": message_text, "is_user": True},
        )
        await self.send(text_data=user_message_html)

        # Built-in command
        if trimmed.lower() == "ping":
            pong_message_html = render_to_string(
                "chat/ws/chat_message.html",
                {"message_text": "pong", "is_system": True},
            )
            await self.send(text_data=pong_message_html)
            return

        # Chat mode (OpenAI)
        self.messages.append({"role": "user", "content": message_text})

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
            if getattr(chunk, "usage", None):
                usage = chunk.usage
            if getattr(chunk, "choices", None) and chunk.choices and getattr(chunk.choices[0].delta, "content", None):
                message_chunk = (chunk.choices[0].delta.content or "")
                formatted_chunk = message_chunk.replace("\n", "<br>")
                await self.send(text_data=f'<div id="{message_id}" hx-swap-oob="beforeend">{formatted_chunk}</div>')
                chunks.append(message_chunk)

        if usage:
            try:
                print(f"Total tokens used: {usage.total_tokens}")
            except Exception:
                pass

        # add the full bot response to the chat history
        self.messages.append({"role": "assistant", "content": "".join(chunks)})
