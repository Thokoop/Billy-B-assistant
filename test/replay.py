import os
import sys
import wave

import numpy as np
from scipy.signal import resample


# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import core.movements
from core.audio import (
    CHUNK_MS,
    RESPONSE_HISTORY_DIR,
    detect_devices,
    ensure_playback_worker_started,
    play_random_wake_up_clip,
    playback_done_event,
    playback_queue,
)


# Detect audio devices and start playback worker
detect_devices()
ensure_playback_worker_started(CHUNK_MS)

# 🐟 Play a random wake-up clip first
wake_up_clip = play_random_wake_up_clip()
if wake_up_clip:
    print(f"🎤 Playing wake-up clip: {wake_up_clip}")
    playback_queue.join()  # Wait for clip to finish

# 🎧 Now play the response-1.wav
file_path = os.path.join(RESPONSE_HISTORY_DIR, "response-1.wav")
if not os.path.exists(file_path):
    print("❌ No response-1.wav found.")
    exit(1)

GAIN = 1.5  # Example: +50% louder

with wave.open(file_path, 'rb') as wf:
    rate = wf.getframerate()
    channels = wf.getnchannels()
    print(f"🎧 Playing back: {file_path} ({rate} Hz, {channels} channel(s))")

    chunk_size = int(24000 * CHUNK_MS / 1000)
    while True:
        frames = wf.readframes(chunk_size)
        if not frames:
            break
        samples = np.frombuffer(frames, dtype=np.int16)

        if channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1).astype(np.int16)

        if rate != 24000:
            new_len = int(len(samples) * 24000 / rate)
            samples = resample(samples, new_len).astype(np.int16)

        # 🎛 Apply Gain
        samples = np.clip(samples * GAIN, -32768, 32767).astype(np.int16)

        playback_queue.put(samples.tobytes())

playback_queue.put(None)  # Signal end of playback
playback_done_event.wait()
core.movements.stop_all_motors()
print("✅ Playback complete.")
