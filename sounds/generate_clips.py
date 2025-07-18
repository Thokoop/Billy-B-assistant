import asyncio
import base64
import json
import os
import wave

import websockets.legacy.client
from dotenv import load_dotenv


# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE = os.getenv("VOICE", "ballad")

# Output path
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "wake-up")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Wake-up clip prompts
CLIPS = [
    "HUH?",
    "huh?",
    "Yeah?",
    "Hmmmm?",
    "Hmm",
    "sup?",
    "Mmm?",
    "Uh huh?",
    "Ugh",
    "Yes?",
    "Hey!",
    "Hey",
    "Yo",
    "Oi!",
    "Whaaaaazaaaaaaaaapp",
]


async def generate_clip(text, index):
    print(f"\n🔊 Generating clip {index}: {text}")

    uri = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "openai-beta": "realtime=v1",
    }

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
                    "instructions": "Always respond by speaking the exact user text out loud. Do not change or rephrase anything!",
                },
            })
        )

        # Step 2: Send text
        await ws.send(
            json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
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

        print("✅ Prompt sent, waiting for response...")

        full_audio = bytearray()

        async for message in ws:
            parsed = json.loads(message)
            #             print("📥", json.dumps(parsed, indent=2))

            if parsed["type"] in ("response.audio", "response.audio.delta"):
                b64 = parsed.get("audio") or parsed.get("delta")
                if b64:
                    full_audio.extend(base64.b64decode(b64))

            if parsed["type"] == "response.done":
                break

        if full_audio:
            wav_path = os.path.join(OUTPUT_DIR, f"{index}.wav")
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(full_audio)
            print(f"✅ Saved: {wav_path} ({len(full_audio)} bytes)")
        else:
            print(f"⚠️ No audio received for clip {index}: {text}")


async def main():
    for i, text in enumerate(CLIPS, start=1):
        await generate_clip(text, i)


if __name__ == "__main__":
    asyncio.run(main())
