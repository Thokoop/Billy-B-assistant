import asyncio
import shutil
import signal
import sys
import threading
import traceback
from pathlib import Path


# --- Ensure .env exists ---
def ensure_env_file():
    env_path = Path(".env")
    env_example_path = Path(".env.example")

    if not env_path.exists():
        if env_example_path.exists():
            shutil.copy(env_example_path, env_path)
            print("✅ .env file created from .env.example")
            print(
                "⚠️  Please review the .env file and update your API key and other settings."
            )
        else:
            print("❌ Neither .env nor .env.example found. Exiting.")
            sys.exit(1)


ensure_env_file()

# --- Now load env ---
from dotenv import load_dotenv


load_dotenv()

# --- Imports that might use environment variables ---
import core.button
from core.audio import playback_queue
from core.movements import start_motor_watchdog, stop_all_motors
from core.mqtt import start_mqtt, stop_mqtt


def signal_handler(sig, frame):
    print("\n👋 Exiting cleanly (signal received).")
    playback_queue.put(None)
    stop_all_motors()
    stop_mqtt()
    sys.exit(0)


main_event_loop = asyncio.get_event_loop()


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    threading.Thread(target=start_mqtt, daemon=True).start()
    start_motor_watchdog()
    core.button.start_loop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Unhandled exception occurred:", e)
        traceback.print_exc()
        stop_all_motors()
        stop_mqtt()
        sys.exit(1)
