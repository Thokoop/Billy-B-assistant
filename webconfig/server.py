import configparser
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading

import numpy as np
import sounddevice as sd
from dotenv import dotenv_values, find_dotenv, set_key
from flask import Flask, Response, jsonify, render_template, request
from packaging.version import parse as parse_version


# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import config as core_config


app = Flask(__name__)

# Load and cache environment variables from .env
ENV_PATH = find_dotenv()
CONFIG_KEYS = [
    "OPENAI_API_KEY",
    "VOICE",
    "MIC_TIMEOUT_SECONDS",
    "SILENCE_THRESHOLD",
    "MQTT_HOST",
    "MQTT_PORT",
    "MQTT_USERNAME",
    "MQTT_PASSWORD",
    "HA_HOST",
    "HA_TOKEN",
    "HA_LANG",
    "MIC_PREFERENCE",
    "SPEAKER_PREFERENCE",
]

WEBCONFIG_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(WEBCONFIG_DIR, ".."))
PERSONA_PATH = os.path.join(PROJECT_ROOT, "persona.ini")
VERSIONS_PATH = os.path.join(PROJECT_ROOT, "versions.ini")
ALLOW_RC_TAGS = os.getenv("ALLOW_RC_TAGS", "false").lower() == "true"

rms_queue = queue.Queue()
mic_check_running = False


def load_env():
    return {
        **{key: str(getattr(core_config, key, "")) for key in CONFIG_KEYS},
        "VOICE_OPTIONS": [
            "ash",
            "ballad",
            "coral",
            "sage",
            "verse",
            "alloy",
            "echo",
            "fable",
            "nova",
        ],
    }


def load_versions():
    config = configparser.ConfigParser()
    if not os.path.exists(VERSIONS_PATH):
        example_path = os.path.join(PROJECT_ROOT, "versions.ini.example")
        if os.path.exists(example_path):
            shutil.copy(example_path, VERSIONS_PATH)
        else:
            config["version"] = {"current": "unknown", "latest": "unknown"}
            with open(VERSIONS_PATH, "w") as f:
                config.write(f)
    config.read(VERSIONS_PATH)
    return config


def save_versions(current, latest):
    if not current or not latest:
        print("[save_versions] Refusing to save empty version")
        return
    config = configparser.ConfigParser()
    config["version"] = {"current": current, "latest": latest}
    with open(VERSIONS_PATH, "w") as f:
        config.write(f)


def get_current_version():
    return load_versions()["version"].get("current", "unknown")


def set_current_version(version):
    config = load_versions()
    config["version"]["current"] = version
    with open(VERSIONS_PATH, "w") as f:
        config.write(f)


def get_usb_pcm_card_index():
    preference = core_config.SPEAKER_PREFERENCE.lower()

    try:
        output = subprocess.check_output(["aplay", "-l"], text=True)
        cards = re.findall(
            r"card (\d+): ([^\s]+) \[(.*?)\], device (\d+): (.*?) \[", output
        )

        for card_index, shortname, longname, device_index, desc in cards:
            name_combined = f"{shortname} {longname} {desc}".lower()
            if preference in name_combined:
                return int(card_index)

        # Fallback to any USB Audio device if no match
        for card_index, _, longname, _, _ in cards:
            if "usb audio" in longname.lower():
                return int(card_index)

        return None
    except Exception as e:
        print("Failed to detect speaker card:", e)
        return None


def get_usb_capture_card_index():
    preference = (core_config.MIC_PREFERENCE or "").lower()

    try:
        output = subprocess.check_output(["arecord", "-l"], text=True)
        cards = re.findall(
            r"card (\d+): ([^\s]+) \[(.*?)\], device (\d+): (.*?) \[", output
        )

        for card_index, shortname, longname, device_index, desc in cards:
            name_combined = f"{shortname} {longname} {desc}".lower()
            if preference in name_combined:
                return int(card_index)

        # Fallback to any USB Audio device if no match
        for card_index, _, longname, _, _ in cards:
            if "usb" in longname.lower():
                return int(card_index)

        return None
    except Exception as e:
        print("Failed to detect mic card:", e)
        return None


def get_mic_gain_numid(card_index):
    try:
        output = subprocess.check_output(
            ["amixer", "-c", str(card_index), "controls"], text=True
        )
        for line in output.splitlines():
            if "Mic Capture Volume" in line:
                match = re.search(r"numid=(\d+)", line)
                if match:
                    return int(match.group(1))
    except Exception as e:
        print("Failed to get mic gain numid:", e)
    return None


def audio_callback(indata, frames, time_info, status):
    if not mic_check_running:
        raise sd.CallbackStop()
    rms = float(np.sqrt(np.mean(np.square(indata))))
    rms_queue.put(rms)


@app.route("/")
def index():
    return render_template("index.html", config=load_env())


@app.route("/version")
def version_info():
    versions = load_versions()
    current = versions["version"].get("current", "unknown")
    latest = versions["version"].get("latest", "unknown")
    return jsonify({
        "current": current,
        "latest": latest,
        "update_available": current != latest and latest != "unknown",
    })


@app.route("/update", methods=["POST"])
def perform_update():
    versions = load_versions()
    current = versions["version"].get("current", "unknown")
    latest = versions["version"].get("latest", "unknown")
    if current == latest or latest == "unknown":
        return jsonify({"status": "up-to-date", "version": current})
    try:
        subprocess.check_call(["git", "fetch"], cwd=PROJECT_ROOT)
        subprocess.check_call(
            ["git", "checkout", "--force", f"{latest}"], cwd=PROJECT_ROOT
        )
        subprocess.check_call(["sudo", "systemctl", "restart", "billy.service"])
        subprocess.check_call([
            "sudo",
            "systemctl",
            "restart",
            "billy-webconfig.service",
        ])
        set_current_version(latest)
        return jsonify({"status": "updated", "version": latest})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": str(e)}), 500


def restart_webconfig_service():
    subprocess.run(["sudo", "systemctl", "restart", "billy-webconfig.service"])
    subprocess.run(["sudo", "systemctl", "restart", "billy.service"])


def fetch_latest_tag():
    try:
        show_rc = dotenv_values().get("SHOW_RC_VERSIONS", "false").lower() == "true"
        output = subprocess.check_output(
            [
                "curl",
                "-s",
                "https://api.github.com/repos/Thokoop/Billy-B-assistant/tags",
            ],
            text=True,
        )
        tags = json.loads(output)
        filtered = [
            tag["name"]
            for tag in tags
            if show_rc or not re.search(r"-?rc\d*$", tag["name"], re.IGNORECASE)
        ]
        if filtered:
            return max(filtered, key=lambda v: parse_version(v.lstrip("v")))
        return "unknown"
    except Exception as e:
        print("Failed to fetch latest tag:", e)
        return "unknown"


versions = load_versions()
latest = fetch_latest_tag()
save_versions(versions["version"].get("current", "unknown"), latest)


@app.route("/save", methods=["POST"])
def save():
    data = request.json
    for key, value in data.items():
        if key in CONFIG_KEYS:
            set_key(ENV_PATH, key, value)
    threading.Thread(target=restart_webconfig_service).start()
    return jsonify({"status": "ok"})


@app.route("/config")
def get_config():
    return jsonify(load_env())


@app.route("/logs")
def logs():
    try:
        output = subprocess.check_output([
            "journalctl",
            "-u",
            "billy.service",
            "-n",
            "100",
            "--no-pager",
            "--output=short",
        ])
        return jsonify({"logs": output.decode("utf-8")})
    except subprocess.CalledProcessError as e:
        return jsonify({"logs": "Failed to retrieve logs", "error": str(e)}), 500


@app.route("/service/<action>")
def control_service(action):
    if action not in ["start", "stop", "restart"]:
        return jsonify({"error": "Invalid action"}), 400
    try:
        subprocess.check_call(["sudo", "systemctl", action, "billy.service"])
        return jsonify({"status": "success", "action": action})
    except subprocess.CalledProcessError:
        return jsonify({"error": "Failed to run systemctl"}), 500


@app.route("/service/status")
def service_status():
    try:
        output = subprocess.check_output(
            ["systemctl", "is-active", "billy.service"], stderr=subprocess.STDOUT
        )
        return jsonify({"status": output.decode("utf-8").strip()})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": e.output.decode("utf-8").strip()})


@app.route("/persona", methods=["GET"])
def get_persona():
    config = configparser.ConfigParser()
    config.read(PERSONA_PATH)
    return jsonify({
        "PERSONALITY": dict(config["PERSONALITY"]) if "PERSONALITY" in config else {},
        "BACKSTORY": dict(config["BACKSTORY"]) if "BACKSTORY" in config else {},
        "META": config["META"].get("instructions", "") if "META" in config else "",
    })


@app.route("/persona", methods=["POST"])
def save_persona():
    data = request.json
    config = configparser.ConfigParser()
    config["PERSONALITY"] = {k: str(v) for k, v in data.get("PERSONALITY", {}).items()}
    config["BACKSTORY"] = data.get("BACKSTORY", {})
    config["META"] = {"instructions": data.get("META", "")}
    with open(PERSONA_PATH, "w") as f:
        config.write(f)
    return jsonify({"status": "ok"})


@app.route("/speaker-test", methods=["POST"])
def speaker_test():
    try:
        card_index = get_usb_pcm_card_index()
        if card_index is None:
            return jsonify({"error": "No matching speaker card found"}), 404

        device = f"plughw:{card_index},0"
        sound_path = os.path.join(PROJECT_ROOT, "sounds", "speakertest.wav")
        subprocess.Popen([
            "aplay",
            "-D",
            device,
            sound_path,
        ])

        return jsonify({"status": f"playing on {device}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/mic-check")
def mic_check():
    def rms_stream_generator():
        global mic_check_running
        mic_check_running = True
        try:
            with sd.InputStream(callback=audio_callback):
                while mic_check_running:
                    try:
                        rms = rms_queue.get(timeout=1.0)
                        payload = {
                            "rms": round(rms, 4),
                            "threshold": round(float(core_config.SILENCE_THRESHOLD), 4),
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                    except queue.Empty:
                        continue
        except Exception as e:
            print("RMS stream error:", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(rms_stream_generator(), mimetype="text/event-stream")


@app.route("/mic-check/stop")
def mic_check_stop():
    global mic_check_running
    mic_check_running = False
    return jsonify({"status": "stopped"})


@app.route("/mic-gain", methods=["GET", "POST"])
def mic_gain():
    card_index = (
        get_usb_capture_card_index()
    )  # You’ll need to write this if it doesn’t exist yet
    numid = get_mic_gain_numid(card_index)
    if card_index is None or numid is None:
        return jsonify({"error": "Could not determine mic card or control ID"}), 500

    if request.method == "GET":
        try:
            output = subprocess.check_output(
                ["amixer", "-c", str(card_index), "cget", f"numid={numid}"], text=True
            )
            match = re.search(r": values=(\d+)", output)
            gain = int(match.group(1)) if match else None
            return jsonify({"gain": gain})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "POST":
        try:
            data = request.get_json()
            value = int(data.get("value", 8))
            if 0 <= value <= 16:  # or the correct max based on `amixer` output
                subprocess.check_call([
                    "amixer",
                    "-c",
                    str(card_index),
                    "cset",
                    f"numid={numid}",
                    str(value),
                ])
                return "OK"
            return jsonify({"error": "Mic gain must be between 0 and 16"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Unsupported method"}), 405


@app.route("/volume", methods=["GET", "POST"])
def volume():
    card_index = get_usb_pcm_card_index()
    if card_index is None:
        return jsonify({"error": "Could not determine speaker card"}), 500

    try:
        if request.method == "GET":
            output = subprocess.check_output(
                ["amixer", "-c", str(card_index), "get", "PCM"], text=True
            )
            match = re.search(r"\[(\d{1,3})%\]", output)
            if match:
                return jsonify({"volume": int(match.group(1))})
            return jsonify({"error": "Could not parse volume"}), 500

        if request.method == "POST":
            data = request.get_json()
            value = data.get("volume")
            if value is None:
                return jsonify({"error": "Missing volume"}), 400

            value = int(value)
            if 0 <= value <= 100:
                subprocess.check_call([
                    "amixer",
                    "-c",
                    str(card_index),
                    "set",
                    "PCM",
                    f"{value}%",
                ])
                return jsonify({"volume": value})
            return jsonify({"error": "Volume must be 0–100"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/device-info")
def device_info():
    try:
        devices = sd.query_devices()
        mic_name = "Unknown"
        speaker_name = "Unknown"
        for dev in devices:
            if (
                mic_name == "Unknown"
                and dev["max_input_channels"] > 0
                and (
                    not core_config.MIC_PREFERENCE
                    or core_config.MIC_PREFERENCE.lower() in dev["name"].lower()
                )
            ):
                mic_name = dev["name"]
            if (
                speaker_name == "Unknown"
                and dev["max_output_channels"] > 0
                and (
                    not core_config.SPEAKER_PREFERENCE
                    or core_config.SPEAKER_PREFERENCE.lower() in dev["name"].lower()
                )
            ):
                speaker_name = dev["name"]
        return jsonify({"mic": mic_name, "speaker": speaker_name})
    except Exception as e:
        return jsonify({"mic": "Unknown", "speaker": "Unknown", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
