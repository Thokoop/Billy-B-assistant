import asyncio
import base64
import json

import websockets.legacy.client

from core.audio import (
    ensure_playback_worker_started,
    playback_queue,
    rotate_and_save_response_audio,
)
from core.config import CHUNK_MS, INSTRUCTIONS, OPENAI_API_KEY, VOICE


async def say(text: str, literal: bool = True):
    print(f"🗣️ say() called with text={text!r} | literal={literal}")

    uri = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "openai-beta": "realtime=v1",
    }

    instructions = (
        INSTRUCTIONS + "\n\n"
        "If the user message begins with anything other than [[PROMPT]], Override for this turn while maintaining your tone and accent:"
        "say the user's message **verbatim**, word for word, with no additions or reinterpretation. "
        "Maintain personality, but do NOT rephrase or expand."
    )

    try:
        async with websockets.legacy.client.connect(uri, extra_headers=headers) as ws:
            # Step 1: Start session
            await ws.send(
                json.dumps({
                    "type": "session.update",
                    "session": {
                        "voice": VOICE,
                        "modalities": ["text", "audio"],
                        "output_audio_format": "pcm16",
                        "turn_detection": {"type": "semantic_vad"},
                        "instructions": instructions,
                    },
                })
            )
            print("🛰️ Session started")

            # Step 2: Send text
            await ws.send(
                json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": f"{text}"}],
                    },
                })
            )

            # Step 3: Force response
            await ws.send(
                json.dumps({
                    "type": "response.create",
                    "response": {"modalities": ["audio", "text"]},
                })
            )
            print("📤 Prompt sent, waiting for response...")

            full_audio = bytearray()
            full_text = ""

            # Ensure playback thread is running BEFORE putting anything in the queue
            ensure_playback_worker_started(CHUNK_MS)

            async for message in ws:
                parsed = json.loads(message)

                # Capture audio
                if parsed["type"] in ("response.audio", "response.audio.delta"):
                    b64 = parsed.get("audio") or parsed.get("delta")
                    if b64:
                        chunk = base64.b64decode(b64)
                        playback_queue.put(chunk)
                        full_audio.extend(chunk)

                # Capture text
                if parsed["type"] in (
                    "response.text.delta",
                    "response.audio_transcript.delta",
                ):
                    delta = parsed.get("delta")
                    if delta:
                        full_text += delta

                if parsed["type"] == "response.done":
                    await ws.send(json.dumps({"type": "session.end"}))
                    break

            print(f"✅ Audio received: {len(full_audio)} bytes")
            print(f"📝 Transcript: {full_text.strip()}")

            # Save + enqueue playback
            rotate_and_save_response_audio(full_audio)

            # Signal end of playback
            playback_queue.put(None)

            # Wait for playback to complete
            await asyncio.to_thread(playback_queue.join)

    except Exception as e:
        print(f"❌ say() failed: {e}")
