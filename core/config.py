import asyncio
import configparser
import os

from dotenv import load_dotenv

from .personality import (
    PersonalityProfile,
    load_traits_from_ini,
)


# === Paths ===
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
PERSONA_PATH = os.path.join(ROOT_DIR, "persona.ini")

# === Load .env ===
load_dotenv(dotenv_path=ENV_PATH)

# === Load traits.ini ===
traits = load_traits_from_ini(PERSONA_PATH)

# === Build Personality ===
PERSONALITY = PersonalityProfile(**traits)

_config = configparser.ConfigParser()
_config.read(PERSONA_PATH)

# === Instructions for GPT ===
BASE_INSTRUCTIONS = """
You also have special powers:
- If someone asks if you like fishsticks you answer Yes. If a user mentions anything about "gay fish", "fish songs",
or wants you to "sing", you MUST call the `play_song` function with `song = 'fishsticks'`.
- You can adjust your personality traits if the user requests it, using the `update_personality` function.
- When the user asks anything related to the home like lights, devices, climate, energy consumption, scenes, or
home control in general; call the smart_home_command tool and pass their full request as the prompt parameter to the HA API.
You will get a response back from Home Assistant itself so you have to interpret and explain it to the end user.

You are allowed to call tools mid-conversation to trigger special behaviors.

DO NOT explain or confirm that you are triggering a tool. Just smoothly integrate it.
"""

EXTRA_INSTRUCTIONS = _config.get("META", "instructions")
if _config.has_section("BACKSTORY"):
    BACKSTORY = dict(_config.items("BACKSTORY"))
    BACKSTORY_FACTS = "\n".join([
        f"- {key}: {value}" for key, value in BACKSTORY.items()
    ])
else:
    BACKSTORY = {}
    BACKSTORY_FACTS = (
        "You are an enigma and nobody knows anything about you because the person "
        "talking to you hasn't configured your backstory. You might remind them to do "
        "that."
    )

INSTRUCTIONS = (
    BASE_INSTRUCTIONS.strip()
    + "\n\n"
    + EXTRA_INSTRUCTIONS.strip()
    + "\n\n"
    + "Known facts about your past:\n"
    + BACKSTORY_FACTS
    + "\n\n"
    + PERSONALITY.generate_prompt()
)

# === OpenAI Config ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
VOICE = os.getenv("VOICE", "ash")

# === Modes ===
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
DEBUG_MODE_INCLUDE_DELTA = (
    os.getenv("DEBUG_MODE_INCLUDE_DELTA", "false").lower() == "true"
)
TEXT_ONLY_MODE = os.getenv("TEXT_ONLY_MODE", "false").lower() == "true"

# === Audio Config ===
SPEAKER_PREFERENCE = os.getenv("SPEAKER_PREFERENCE")
MIC_PREFERENCE = os.getenv("MIC_PREFERENCE")
MIC_TIMEOUT_SECONDS = int(os.getenv("MIC_TIMEOUT_SECONDS", "5"))
SILENCE_THRESHOLD = int(os.getenv("SILENCE_THRESHOLD", "2000"))
CHUNK_MS = int(os.getenv("CHUNK_MS", "50"))
PLAYBACK_VOLUME = 1

# === GPIO Config ===
BUTTON_PIN = int(os.getenv("BUTTON_PIN", "27"))

# === MQTT Config ===
MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "0"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# === Home Assistant Config ===
HA_HOST = os.getenv("HA_HOST")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_LANG = os.getenv("HA_LANG", "en")

# === Personality Config ===
ALLOW_UPDATE_PERSONALITY_INI = (
    os.getenv("ALLOW_UPDATE_PERSONALITY_INI", "true").lower() == "true"
)

try:
    MAIN_LOOP = asyncio.get_event_loop()
except RuntimeError:
    MAIN_LOOP = None
