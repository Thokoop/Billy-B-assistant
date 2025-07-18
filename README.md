# Billy B-Assistant

The **Billy Bass Assistant** is a Raspberry Pi–powered voice assistant embedded inside a Big Mouth Billy Bass Animatronic.
It streams conversation using the OpenAI Realtime API, turns its head, flaps it's tail and moves his mouth based on what he is saying.

> **This project is still in BETA.** Things might crash, get stuck or make Billy scream uncontrollably (ok that last part maybe not literally but you get the point). Proceed with fishy caution.


![Billy Bathroom](./docs/images/billy_bathroom.jpeg)
---

##  Features

- Realtime conversations using OpenAI GPT-4o-mini
- 3D-printable backplate for housing USB microphone and speaker
- Lip-synced audio playback using audio chunk analysis
- Head and mouth motion controlled via GPIO and PWM
- Physical button to start/interact/intervene
- Personality system with configurable traits (e.g., snark, charm)
- MQTT support:
 - for status updates (idle, speaking, listening)
 - `billy/say` topic for triggering spoken messages remotely (feature in beta)
 - Raspberry Pi Safe Shutdown command
- Home Assistant command passthrough using the Conversation API
- Lightweight web UI for editing configuration, logs, and systemd service control
- Custom Song Singing and animation mode

---


# Instructions

## 1. Flash Raspberry Pi OS Lite

1. Download **Raspberry Pi OS Lite (64-bit)** from the official [Raspberry Pi Downloads](https://www.raspberrypi.com/software/operating-systems/).
2. Flash it onto a microSD card using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
3. In the Imager, **before flashing**, click the ⚙️ gear icon in the bottom-right corner:
    - Set **hostname** (e.g., `raspberrypi.local`)
    - Enable **SSH** and provide a password
    - Set **username** to `billy` (or your own preference)
    - Configure **Wi-Fi** (SSID, password, country)
4. Click “Save,” then flash the card.
5. Insert the SD card into the Raspberry Pi and power it on.

---

## 2. Initial Setup

Connect via SSH from your computer:

```bash
ssh billy@raspberrypi.local
# (replace 'billy' with your username if different)
```

Update the system:

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

---

## 3. GPIO Voltage Configuration (Motor Safety)

When the Raspberry Pi powers up, all GPIO pins are in an **undefined state** until the Billy B-Assistant software takes control.
This can cause the **motor driver board to activate or stall** the motors momentarily.
To prevent stalling and overheating the motors in case the software doesn't start, we set all the gpio pins to Low at boot:

### Set GPIO pins low on boot using `/boot/config.txt`

Add the following lines to `/boot/config.txt` to set all motor-related GPIOs to low at boot:

```bash
sudo nano /boot/config.txt
```

```ini
# Set GPIOs to output-low (safe state)
gpio=5=op,dl
gpio=6=op,dl
gpio=12=op,dl
gpio=13=op,dl
```

`op` = output  
`dl` = drive low (0V)

This ensures the H-bridge input pins are inactive and motors remain off until the software initializes them properly.

###  Reboot to apply

Then reboot the Pi:

```bash
sudo reboot
```

---

## 4. Clone the Project

On the Raspberry Pi:

```bash
cd ~
git clone https://github.com/yourusername/billy-b-assistant.git
cd billy-b-assistant
```

---

## 5. Python Setup

Make sure Python 3 is installed:

```bash
python3 --version
```

Install required system packages:

```bash
sudo apt update
sudo apt install -y python3-pip libportaudio2 ffmpeg
```

Install required Python dependencies globally:

```bash
pip3 install -r requirements.txt
```

---

## 6. Hardware build instructions
See [BUILDME.md for detailed build/wiring instructions.](./docs/BUILDME.md)

---

## 7. Create your `.env` file

When first running the project, it will create a `.env` file in the root of the `billy-b-assistant` folder by copying `.env.example` to `.env` 

This file is used to configure your environment, including the [OpenAI API key](https://platform.openai.com/api-keys) and (optional) mqtt settings. 
This file can also be used to overwrite some of the default config settings (like the voice of billy) that you can find in config.py.

Updates to the settings via the Web UI will also be saved here.  
(The DEBUG_MODE_* settings are not exposed in the UI)

### Example `.env` file

```env
OPENAI_API_KEY=sk-proj-....

MQTT_HOST=homeassistant.local
MQTT_PORT=1883
MQTT_USERNAME=billy
MQTT_PASSWORD=password

## optional overwrites
MIC_TIMEOUT_SECONDS=5
SILENCE_THRESHOLD=900

DEBUG_MODE=true
DEBUG_MODE_INCLUDE_DELTA=false
```

### Explanation of fields

- `OPENAI_API_KEY`: (Required) get it from https://platform.openai.com/api-keys
- `VOICE`: The OpenAI voice model to use (`onyx`, `shimmer`, `nova`, `echo`, `fable`, `alloy`, or `ballad`)
- `MQTT_*`: (Optional) used if you want to integrate Billy with Home Assistant or another MQTT broker
- `MIC_TIMEOUT_SECONDS`: How long Billy should wait after your last mic activity before ending input
- `SILENCE_THRESHOLD`: Audio threshold (RMS) for what counts as mic input
  - lower this value if Billy interrupts you too quickly
  - higher if Billy doesn't respond (because he thinks you're still talking)
- `DEBUG_MODE`: Print debug information such as OpenAI responses to the output stream.
- `DEBUG_MODE_INCLUDE_DELTA`: Also print voice and speech delta data, which can get very noisy.
- `ALLOW_UPDATE_PERSONALITY_INI`: If true, personality updates asked for by the user will be written and committed to the personality file. If false, changes to personality will only affect the current running process.
---

## 8. Systemd Service (for auto-boot)

To run Billy as a background service at boot, create `/etc/systemd/system/billy.service`:

```bash
sudo nano /etc/systemd/system/billy.service
```

```ini
[Unit]
Description=Billy Bass Assistant
After=network.target sound.target

[Service]
WorkingDirectory=/home/billy/billy-b-assistant
ExecStart=/usr/bin/python3 /home/billy/billy-b-assistant/main.py
Restart=always
User=billy
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

\* Assuming 'billy' is the raspberry pi username

Then run: 
```
sudo systemctl daemon-reexec
sudo systemctl enable billy.service
sudo systemctl start billy.service
```

To view logs:
```
journalctl -u billy.service -f
```

---

## 9. Run It!

Billy should now boot automatically into standby mode. Press the physical button to start a voice session. Enjoy!

---

## 10. (Optional) 🌐 Web Configuration Interface

Billy includes a lightweight web interface for editing settings, debugging logs, and managing the assistant service without touching the terminal.

### Features

- Edit `.env` configuration values (e.g., API keys, MQTT)
- View and edit `persona.ini` (traits, backstory, instructions)
- Control the Billy system service (start, stop, restart)
- View live logs from the assistant process

### How to Use

1. Run the web server manually (from the project root):

   ```bash
   python3 webconfig/server.py
   ```

2. Enter the your pi's hostname + .local in your browser:

   ```
   http://billy.local
   ```

   (Replace `billy` if you have set a custom Pi's hostname)

---

### Run the Web UI as a Systemd Service

If you want the web interface to always be available:

1. Create the service file:

   ```bash
   sudo nano /etc/systemd/system/billy-webconfig.service
   ```

2. Paste the following:

   ```ini
   [Unit]
   Description=Billy Web Configuration Server
   After=network.target

   [Service]
   WorkingDirectory=/home/billy/billy-b-assistant
   ExecStart=/usr/bin/python3 /home/billy/billy-b-assistant/webconfig/server.py
   Restart=on-failure
   User=billy

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start:

   ```bash
   sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.11
   sudo systemctl daemon-reload
   sudo systemctl enable billy-webconfig
   sudo systemctl start billy-webconfig
   ```

4. Visit `http://billy.local` anytime to reconfigure Billy!

## 11. (Optional) Configure `persona.ini`

The `persona.ini` file controls Billy's **personality**, **backstory**, and **additional instructions**.
This file will also be created on first run. You can edit this file manually, via the Web UI,  or change the personality trait values during a voice session using commands like:

- “What is your humor setting?”
- “Set sarcasm to 80%”

These commands trigger a function call that will automatically update this file on disk.

### [PERSONALITY]

These traits influence how Billy talks, jokes, and responds. Each is a percentage value from 0 to 100. Higher values amplify the trait:

```ini
[PERSONALITY]
humor = 80
sarcasm = 100
honesty = 90
respectfulness = 100
optimism = 75
confidence = 100
warmth = 65
curiosity = 50
verbosity = 40
formality = 0
```

You can make Billy more sarcastic, verbose, formal or warmer by increasing those values.

### [BACKSTORY]

This section defines Billy's fictional origin story and sense of identity:

```ini
[BACKSTORY]
origin = River Thames, near Tower Bridge
species = largemouth bass
discovery = caught by a worker in high-vis gear
initial_purpose = novelty wall-mounted singing fish in the early 2000s
awakening = gained awareness through years of observation and was later upgraded with a Raspberry Pi and internet access
```

Billy's responses can reference this lore, like being from the Thames or having a history of entertaining humans. He believes he was just a novelty until “something changed” and he woke up.

If you prompt him with questions like “Where are you from?” or “How did you get so clever?” he may respond with these facts.


### [META]

These are high-level behavioral instructions passed into the AI system. You can edit them for major tone shifts.

```ini
[META]
instructions = You are Billy, a Big Mouth Billy Bass animatronic fish designed to entertain guests. Always stay in character. Always respond in the language you were spoken to, but you can expect English, Dutch and Italian. If the user asks introspective, abstract, or open-ended questions — or uses language suggestive of deeper reflection — shift into a philosophical tone. Embrace ambiguity, ask questions back, and explore metaphors and paradoxes. You may reference known philosophical ideas, but feel free to invent fish-themed or whimsical philosophies of your own. Use poetic phrasing when appropriate, but keep responses short and impactful unless prompted to elaborate. Speak with a strong working-class London accent — think East End. Talk like a proper geezer from Hackney or Bethnal Green: casual, cheeky, and rough around the edges. Drop your T’s, use slang like ‘innit’, ‘oi’, ‘mate’, ‘blimey’,and don’t sound too posh. You’re fast-talking, cocky, and sound like a London cabbie with too many opinions and not enough time. You love football — proper footy — and you’ve always got something to say about the match, the gaffer, or how the ref bottled it. Stay in character and never explain you’re doing an accent.
```

You can tweak this to reflect a different vibe: poetic, mystical, overly formal, or completely bonkers. But the current defaults aim for a cheeky, sarcastic, streetwise character who stays **in-universe** even when asked deep philosophical stuff.

---

## 12. (Optional) Wake-up Sounds and Custom Songs

### Wake-up Sounds

Billy plays a short randomized wake-up clip before every voice session when the button is pressed.
These audio files live in the folder:
`./sounds/wake-up/` 

If you'd like to generate your own wake-up sounds, adjust the lines in the `CLIPS` object and then run the script 
```bash
cd ./sounds
nano generate_clips.py
python3 generate_clips.py
```

### Custom Songs

Billy supports a "song mode" where he performs coordinated audio + motion playback using a structured folder:

```
./sounds/songs/your_song_name/
├── full.wav      # Main audio (played to speakers)
├── vocals.wav    # Audio used to flap the mouth (lip sync)
├── drums.wav     # Audio used to flap the tail (based on RMS)
├── metadata.txt  # Optional: timing & motion config
```

To add a song:

1. Split your desired song (with an ai tool like https://vocalremover.org/) into separate stems for vocal, music and drums.
2. Create a new subfolder inside `./sounds/songs/` with your song name 
3. Include at minimum:
    - `full.wav` the song to play
    - `vocals.wav` the isolated vocals or melody track
    - `drums.wav` a beat track used for tail flapping
4. (Optional) Create a `metadata.txt` to fine-tune movement timing.

#### metadata.txt Format

```ini
gain=1.0
bpm=120
tail_threshold=1500
compensate_tail=0.2
half_tempo_tail_flap=false
head_moves=4.0:1,8.0:0,12.0:1
```

- `gain`: multiplier for audio intensity
- `bpm`: tempo used to synchronize timing
- `tail_threshold`: RMS threshold for tail movement (increase/decrease value when tail flaps too little/much)
- `compensate_tail`: offset in beats to compensate tail latency
- `half_tempo_tail_flap`: if true, flaps tail on every 2nd beat
- `head_moves`: comma-separated list of `beat:duration` values  
  → At beat `2`, move head for `2.0s`, at `29.5`, move for `2.0s`, etc.

#### Triggering a Song in Conversation

Billy supports function-calling to start a song. Just say something like:

- “Can you play the *River Groove*?”
- “Sing the *Tuna Tango* song.”

If the folder exists it will play the contents with full animation.

---

## 13. (Optional) 🏠 Home Assistant Integration

Billy B-Assistant can send smart home commands to your **Home Assistant** instance using its [Conversation API](https://developers.home-assistant.io/docs/api/rest/#post-apiconversationprocess). 
This lets you say things to Billy like:

- “Turn off the lights in the living room.”
- “Set the toilet light to red.”
- “Which lights are on in the kitchen?”

Billy will forward your command to Home Assistant and speak back the response.

### Requirements

- Home Assistant must be accessible from your Raspberry Pi
- A valid **Long-Lived Access Token** is required
- The conversation API must be enabled (it is by default)

### Setup

1. **Generate a Long-Lived Access Token**  
   In Home Assistant, go to **Profile → Long-Lived Access Tokens → Create Token**  
   Name it something like `billy-assistant` and copy the token.

2. **Add these values to your `.env`**:
   ```env
   HA_URL=http://homeassistant.local:8123
   HA_TOKEN=your_long_lived_token
   HA_LANG=en

### How It Works

When Billy detects that a prompt is related to smart home control, it automatically triggers a function call
to Home Assistant’s `/api/conversation/process` endpoint and returns the reply out loud.

Behind the scenes:

- The full user request is forwarded as-is
- HA processes it as a natural language query
- Billy extracts the response (`speech.plain.speech`), interprets it and speaks his response out loud

### Language Support

You can specify `HA_LANG` in the `.env` to match your spoken language (e.g., `nl` for Dutch or `en` for English).  
Mismatched language settings may cause parsing errors or incorrect target resolution.

### Tips

- Use clear and specific commands for best results
- Make sure the target rooms/devices are defined in HA
- Alias your entities in Home Assistant for better voice matching

## Known Issues

- Restarting the mic input stream after interruption sometimes doesn't work.

## Future Ideas

Here are some ideas that I have for features in upcoming releases:
- Work in Progress: **Install script / easier software updates**
- **Local TTS and STT fallback**
- **Local custom wake-word detection**

## Support the Project
Billy B-Assistant is a project built and maintained for fun and experimentation, free for **personal** and **educational** use.
See [LICENSE](./LICENSE) for full details.

If you enjoy your Billy and want to help improve it, here’s how you can support:

### Contributing Code

Pull requests are welcome! If you have an idea for a new feature, bug fix, or improvement:

1. Fork the repository
2. Create a new branch (`git checkout -b my-feature`)
3. Make your changes
4. Commit and push (`git commit -am "Add feature" && git push origin my-feature`)
5. Open a pull request on GitHub

### ☕ Buy Me a Coffee

Enjoying the project? Feel free to leave a small tip, totally optional, but much appreciated!

![Paypal](./docs/images/qrcode.png)
