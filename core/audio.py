import asyncio
import base64
import glob
import json
import os
import random
import sys
import threading
import time
import wave
from queue import Queue

import numpy as np
import sounddevice as sd
from scipy.signal import resample

from .config import (
    CHUNK_MS,
    MIC_PREFERENCE,
    PLAYBACK_VOLUME,
    SPEAKER_PREFERENCE,
    TEXT_ONLY_MODE,
)
from .movements import (
    flap_from_pcm_chunk,
    interlude,
    move_head,
    move_tail_async,
)


# === Audio Device Globals ===
MIC_DEVICE_INDEX = None
MIC_RATE = None
MIC_CHANNELS = 2
OUTPUT_DEVICE_INDEX = None
OUTPUT_CHANNELS = 2
OUTPUT_RATE = None
CHUNK_SIZE = None
WAKE_UP_DIR = "sounds/wake-up"
RESPONSE_HISTORY_DIR = "sounds/response-history"
os.makedirs(RESPONSE_HISTORY_DIR, exist_ok=True)

playback_queue = Queue()
head_move_queue = Queue()
playback_done_event = threading.Event()
_playback_thread = None
last_played_time = time.time()
song_mode = False
beat_length = 0.5
compensate_tail_beats = 0.0


def detect_devices(debug=False):
    global MIC_DEVICE_INDEX, MIC_RATE, MIC_CHANNELS, CHUNK_SIZE
    global OUTPUT_DEVICE_INDEX, OUTPUT_RATE, OUTPUT_CHANNELS

    devices = sd.query_devices()

    for i, d in enumerate(devices):
        if debug:
            print(
                f"{i}: {d['name']} (inputs: {d['max_input_channels']}, outputs: {d['max_output_channels']})"
            )

        if MIC_DEVICE_INDEX is None and d['max_input_channels'] > 0:
            if (
                MIC_PREFERENCE
                and MIC_PREFERENCE.lower() in d['name'].lower()
                or not MIC_PREFERENCE
            ):
                MIC_DEVICE_INDEX = i

            MIC_RATE = int(d['default_samplerate'])
            MIC_CHANNELS = d['max_input_channels']
            CHUNK_SIZE = int(MIC_RATE * CHUNK_MS / 1000)

        if OUTPUT_DEVICE_INDEX is None and d['max_output_channels'] > 0:
            if (
                SPEAKER_PREFERENCE
                and SPEAKER_PREFERENCE.lower() in d['name'].lower()
                or not SPEAKER_PREFERENCE
            ):
                OUTPUT_DEVICE_INDEX = i

            OUTPUT_RATE = int(d['default_samplerate'])
            OUTPUT_CHANNELS = d['max_output_channels']

    if MIC_DEVICE_INDEX is None or (OUTPUT_DEVICE_INDEX is None and not TEXT_ONLY_MODE):
        print("❌ No suitable input/output devices found.")
        sys.exit(1)


def playback_worker(chunk_ms):
    global last_played_time
    global head_out
    global song_start_time

    interlude_counter = 0
    interlude_target = random.randint(150000, 300000)
    head_move_active = False
    head_move_end_time = 0
    next_head_move = None
    drums_peak = 0
    drums_peak_time = 0
    next_beat_time = 0

    try:
        with sd.OutputStream(
            samplerate=48000, channels=2, dtype='int16', device=OUTPUT_DEVICE_INDEX
        ) as stream:
            print("🔈 Output stream opened")
            while True:
                item = playback_queue.get()
                now = time.time()

                if head_move_active and now >= head_move_end_time:
                    move_head("off")
                    head_out = False
                    head_move_active = False
                    print("🛑 Head move ended")

                if not head_move_active and not head_move_queue.empty():
                    move_time, move_duration = head_move_queue.queue[0]  # peek
                    if now - song_start_time >= move_time:
                        head_move_queue.get()
                        move_head("on")
                        head_out = True
                        head_move_active = True
                        head_move_end_time = now + move_duration
                        print(f"🐟 Head move started for {move_duration:.2f} seconds")

                if item is None:
                    print("🧵 Received stop signal, cleaning up.")
                    try:
                        from .movements import stop_all_motors

                        stop_all_motors()
                    except Exception as e:
                        print(f"❌ Failed to stop motors: {e}")
                    playback_queue.task_done()
                    break

                if isinstance(item, tuple):
                    mode = item[0]
                    if mode == "song":
                        audio_chunk, flap_chunk, rms_drums = item[1], item[2], item[3]

                        flap_from_pcm_chunk(
                            np.frombuffer(flap_chunk, dtype=np.int16), chunk_ms=chunk_ms
                        )

                        if rms_drums > drums_peak:
                            drums_peak = rms_drums
                            drums_peak_time = now

                        adjusted_now = (now - song_start_time) + (
                            compensate_tail_beats * beat_length
                        )
                        elapsed_song_time = now - song_start_time

                        # print(f"[DEBUG] ⏱ elapsed: {elapsed_song_time:.2f}s | 🥁 adjusted: {adjusted_now:.2f}s | 🎯 next beat at {next_beat_time:.2f}s | 🐟 head_move_queue: {list(head_move_queue.queue)}")

                        if adjusted_now >= next_beat_time:
                            if drums_peak > 1500 and not head_out:
                                move_tail_async(duration=0.2)
                            drums_peak = 0
                            drums_peak_time = 0
                            next_beat_time += beat_length

                        mono = np.frombuffer(audio_chunk, dtype=np.int16)
                        resampled = resample(
                            mono, int(len(mono) * 48000 / 24000)
                        ).astype(np.int16)
                        stereo = np.repeat(resampled[:, np.newaxis], 2, axis=1)
                        stereo = np.clip(
                            stereo * PLAYBACK_VOLUME, -32768, 32767
                        ).astype(np.int16)
                        stream.write(stereo)

                    elif mode == "tts":
                        chunk = item[1]
                        mono = np.frombuffer(chunk, dtype=np.int16)
                        chunk_len = int(24000 * chunk_ms / 1000)
                        for i in range(0, len(mono), chunk_len):
                            sub = mono[i : i + chunk_len]
                            if len(sub) == 0:
                                continue
                            flap_from_pcm_chunk(sub, chunk_ms=chunk_ms)
                            resampled = resample(
                                sub, int(len(sub) * 48000 / 24000)
                            ).astype(np.int16)
                            stereo = np.repeat(resampled[:, np.newaxis], 2, axis=1)
                            stereo = np.clip(
                                stereo * PLAYBACK_VOLUME, -32768, 32767
                            ).astype(np.int16)
                            stream.write(stereo)

                            interlude_counter += len(sub)
                            if interlude_counter >= interlude_target:
                                interlude()
                                interlude_counter = 0
                                interlude_target = random.randint(80000, 160000)

                else:
                    chunk = item
                    mono = np.frombuffer(chunk, dtype=np.int16)
                    chunk_len = int(24000 * chunk_ms / 1000)
                    for i in range(0, len(mono), chunk_len):
                        sub = mono[i : i + chunk_len]
                        if len(sub) == 0:
                            continue
                        flap_from_pcm_chunk(sub, chunk_ms=chunk_ms)
                        resampled = resample(sub, int(len(sub) * 48000 / 24000)).astype(
                            np.int16
                        )
                        stereo = np.repeat(resampled[:, np.newaxis], 2, axis=1)
                        stereo = np.clip(
                            stereo * PLAYBACK_VOLUME, -32768, 32767
                        ).astype(np.int16)
                        stream.write(stereo)

                        interlude_counter += len(sub)
                        if interlude_counter >= interlude_target:
                            interlude()
                            interlude_counter = 0
                            interlude_target = random.randint(80000, 160000)

                playback_queue.task_done()
                last_played_time = time.time()

    except Exception as e:
        print(f"❌ Playback stream failed: {e}")
    finally:
        playback_done_event.set()


def ensure_playback_worker_started(chunk_ms):
    global _playback_thread
    if TEXT_ONLY_MODE:
        return
    if not _playback_thread or not _playback_thread.is_alive():
        _playback_thread = threading.Thread(
            target=playback_worker, args=(chunk_ms,), daemon=True
        )
        _playback_thread.start()


def save_audio_to_wav(audio_bytes, filename):
    full_path = os.path.join(RESPONSE_HISTORY_DIR, filename)
    with wave.open(full_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(audio_bytes)
    print(f"🎨 Saved response audio to {full_path}")


def rotate_and_save_response_audio(audio_bytes):
    # Rotate old files first (2 -> 3, 1 -> 2)
    for i in range(2, 0, -1):
        src = os.path.join(RESPONSE_HISTORY_DIR, f"response-{i}.wav")
        dst = os.path.join(RESPONSE_HISTORY_DIR, f"response-{i + 1}.wav")
        if os.path.exists(src):
            os.replace(src, dst)

    save_audio_to_wav(audio_bytes, "response-1.wav")


def handle_incoming_audio_chunk(audio_b64, buffer):
    audio_chunk = base64.b64decode(audio_b64)
    buffer.extend(audio_chunk)
    playback_queue.put(audio_chunk)
    return len(audio_chunk)


def send_mic_audio(ws, samples, loop):
    pcm = (
        resample(samples, int(len(samples) * 24000 / MIC_RATE))
        .astype(np.int16)
        .tobytes()
    )
    try:
        future = asyncio.run_coroutine_threadsafe(
            ws.send(
                json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(pcm).decode("utf-8"),
                })
            ),
            loop,
        )

        # Await the result; avoid race conditions.
        future.result()
    except Exception as e:
        print(f"❌ Failed to send audio chunk: {e}")


def enqueue_wav_to_playback(filepath):
    """Reads a WAV file and enqueues its PCM audio data to the playback queue."""
    with wave.open(filepath, 'rb') as wf:
        if (
            wf.getframerate() != 24000
            or wf.getnchannels() != 1
            or wf.getsampwidth() != 2
        ):
            raise ValueError("WAV file must be 24000 Hz, mono, 16-bit")

        chunk_size = int(24000 * CHUNK_MS / 1000)
        while True:
            frames = wf.readframes(chunk_size)
            if not frames:
                break
            playback_queue.put(frames)


def play_random_wake_up_clip():
    """Select and enqueue a random wake-up WAV file with mouth movement."""
    clips = glob.glob(os.path.join(WAKE_UP_DIR, "*.wav"))
    if not clips:
        print("⚠️ No wake-up clips found.")
        return None

    clip = random.choice(clips)

    # Track how many tasks were pending before enqueue
    already_pending = playback_queue.unfinished_tasks

    # Enqueue the WAV file
    enqueue_wav_to_playback(clip)

    # Wait for exactly those new chunks to finish
    while playback_queue.unfinished_tasks > already_pending:
        time.sleep(0.01)

    return clip


def stop_playback():
    """Immediately stop playback and flush queue."""
    while not playback_queue.empty():
        try:
            playback_queue.get_nowait()
            playback_queue.task_done()
        except Exception:
            break
    playback_done_event.set()


def is_billy_speaking():
    """Return True if Billy is still playing audio."""
    if not audio.playback_done_event.is_set():
        return True
    return bool(not audio.playback_queue.empty())


def reset_for_new_song():
    global \
        last_played_time, \
        song_start_time, \
        next_beat_time, \
        drums_peak, \
        drums_peak_time
    playback_queue.queue.clear()
    head_move_queue.queue.clear()
    playback_done_event.clear()
    last_played_time = time.time()
    song_start_time = time.time()
    next_beat_time = 0
    drums_peak = 0
    drums_peak_time = 0


async def play_song(song_name):
    """Play a full Billy song: main audio, vocals for mouth, drums for tail."""
    import contextlib

    from core import audio
    from core.movements import stop_all_motors
    from core.mqtt import mqtt_publish

    reset_for_new_song()

    SONG_DIR = f"./sounds/songs/{song_name}"
    MAIN_AUDIO = os.path.join(SONG_DIR, "full.wav")
    VOCALS_AUDIO = os.path.join(SONG_DIR, "vocals.wav")
    DRUMS_AUDIO = os.path.join(SONG_DIR, "drums.wav")
    METADATA_FILE = os.path.join(SONG_DIR, "metadata.txt")

    def load_metadata(path):
        metadata = {
            "bpm": None,
            "head_moves": [],
            "tail_threshold": 1500,
            "gain": 1.0,
            "compensate_tail": 0.0,
            "half_tempo_tail_flap": False,
        }
        if not os.path.exists(path):
            print(f"⚠️ No metadata.txt found at {path}")
            return metadata

        with open(path) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    if key == "head_moves":
                        metadata[key] = [
                            (float(v.split(':')[0]), float(v.split(':')[1]))
                            for v in value.split(',')
                        ]
                    elif key in ("bpm", "tail_threshold", "gain", "compensate_tail"):
                        metadata[key] = float(value.strip())
                    elif key == "half_tempo_tail_flap":
                        metadata[key] = value.strip().lower() == "true"
        return metadata

    # --- Load metadata ---
    metadata = load_metadata(METADATA_FILE)
    GAIN = metadata.get("gain", 1.0)
    BPM = metadata.get("bpm", 120)
    tail_threshold = metadata.get("tail_threshold", 1500)
    global compensate_tail_beats
    compensate_tail_beats = metadata.get("compensate_tail", 0.0)
    head_move_schedule = metadata.get("head_moves", [])
    for move in head_move_schedule:
        audio.head_move_queue.put(move)
    half_tempo_tail_flap = metadata.get("half_tempo_tail_flap", False)

    audio.beat_length = 60.0 / BPM
    if metadata.get("half_tempo_tail_flap"):
        audio.beat_length *= 2

    # Start the playback worker, passing the schedule
    audio.song_mode = True
    ensure_playback_worker_started(CHUNK_MS)

    mqtt_publish("billy/state", "playing_song")
    print(f"\n🎧 Playing {song_name} with mouth (vocals) and tail (drums) flaps")

    try:
        with contextlib.ExitStack() as stack:
            wf_main = stack.enter_context(wave.open(MAIN_AUDIO, 'rb'))
            wf_vocals = stack.enter_context(wave.open(VOCALS_AUDIO, 'rb'))
            wf_drums = stack.enter_context(wave.open(DRUMS_AUDIO, 'rb'))

            rate_main = wf_main.getframerate()
            rate_vocals = wf_vocals.getframerate()
            rate_drums = wf_drums.getframerate()

            chunk_size_main = int(rate_main * CHUNK_MS / 1000)
            chunk_size_vocals = int(rate_vocals * CHUNK_MS / 1000)
            chunk_size_drums = int(rate_drums * CHUNK_MS / 1000)

            while True:
                frames_main = wf_main.readframes(chunk_size_main)
                frames_vocals = wf_vocals.readframes(chunk_size_vocals)
                frames_drums = wf_drums.readframes(chunk_size_drums)

                if not frames_main:
                    break

                # --- Main audio (24kHz mono)
                samples_main = np.frombuffer(frames_main, dtype=np.int16)
                samples_main = samples_main.reshape((-1, 2)).mean(axis=1)
                if rate_main == 48000:
                    samples_main = resample(
                        samples_main, len(samples_main) // 2
                    ).astype(np.int16)
                samples_main = np.clip(samples_main * GAIN, -32768, 32767).astype(
                    np.int16
                )

                # --- Vocals (for mouth flap)
                samples_vocals = np.frombuffer(frames_vocals, dtype=np.int16)
                samples_vocals = samples_vocals.reshape((-1, 2)).mean(axis=1)
                if rate_vocals == 48000:
                    samples_vocals = resample(
                        samples_vocals, len(samples_vocals) // 2
                    ).astype(np.int16)
                samples_vocals = np.clip(samples_vocals * GAIN, -32768, 32767).astype(
                    np.int16
                )

                # --- Drums (for tail flap)
                samples_drums = np.frombuffer(frames_drums, dtype=np.int16)
                samples_drums = samples_drums.reshape((-1, 2)).mean(axis=1)
                if rate_drums == 48000:
                    samples_drums = resample(
                        samples_drums, len(samples_drums) // 2
                    ).astype(np.int16)
                samples_drums = np.clip(samples_drums * GAIN, -32768, 32767).astype(
                    np.int16
                )
                rms_drums = np.sqrt(np.mean(samples_drums.astype(np.float32) ** 2))

                # --- Enqueue combined chunk
                audio.playback_queue.put((
                    "song",
                    samples_main.tobytes(),
                    samples_vocals.tobytes(),
                    rms_drums,
                ))

        print("⌛ Waiting for song playback to complete...")
        await asyncio.to_thread(audio.playback_queue.join())

    except Exception as e:
        print(f"❌ Playback failed: {e}")

    finally:
        audio.song_mode = False
        stop_all_motors()
        mqtt_publish("billy/state", "idle")
        print("🎶 Song finished, waiting for button press.")
