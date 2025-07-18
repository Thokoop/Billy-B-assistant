import subprocess
import time

from flask import Flask, render_template_string, request


app = Flask(__name__)

FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Connect Billy to Wi-Fi</title>
  <style>
    body {
      background-color: #111;
      color: #eee;
      font-family: sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 1rem;
    }
    form {
      background: #222;
      padding: 2rem;
      border-radius: 10px;
      box-shadow: 0 0 10px #000;
      width: 100%;
      max-width: 400px;
    }
    label {
      display: block;
      margin-bottom: 1rem;
    }
    input, select, button {
      width: 100%;
      padding: 0.75rem;
      margin-top: 0.5rem;
      border: none;
      border-radius: 5px;
      font-size: 16px;
    }
    button {
      background-color: #4caf50;
      color: white;
      font-weight: bold;
    }
    p {
      margin-top: 1rem;
      text-align: center;
    }
  </style>
</head>
<body>
<h2>Connect Billy to Wi-Fi</h2>
<form method="POST">
  <label>SSID:
    <input name="ssid" required />
  </label>
  <label>Password:
    <input name="password" type="password" required />
  </label>
  <label>Country:
    <select name="country" required>
      <option value="">-- Select your country --</option>
      <option value="US">🇺🇸 United States</option>
      <option value="GB">🇬🇧 United Kingdom</option>
      <option value="DE">🇩🇪 Germany</option>
      <option value="NL">🇳🇱 Netherlands</option>
      <option value="FR">🇫🇷 France</option>
      <option value="ES">🇪🇸 Spain</option>
      <option value="IT">🇮🇹 Italy</option>
      <option value="JP">🇯🇵 Japan</option>
      <option value="KR">🇰🇷 South Korea</option>
      <option value="IN">🇮🇳 India</option>
      <option value="CN">🇨🇳 China</option>
      <option value="BR">🇧🇷 Brazil</option>
      <option value="CA">🇨🇦 Canada</option>
      <option value="AU">🇦🇺 Australia</option>
    </select>
  </label>
  <button type="submit">Connect</button>
</form>
{% if message %}
  <p><strong>{{ message }}</strong></p>
{% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def onboarding():
    message = None
    if request.method == "POST":
        ssid = request.form["ssid"]
        password = request.form["password"]
        country = request.form["country"]

        success = save_wifi_credentials(ssid, password, country)

        if success:
            message = f"✅ Connected to {ssid}! Billy will now reboot or switch to normal mode."
            stop_hotspot_services()
            shutdown_flask_soon()
        else:
            message = f"❌ Failed to connect to {ssid}. Please check your credentials."

    return render_template_string(FORM, message=message)


def save_wifi_credentials(ssid, password, country):
    try:
        # Set Wi-Fi regulatory domain
        subprocess.run(["iw", "reg", "set", country], check=True)

        subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], check=True)

        subprocess.run(["nmcli", "radio", "wifi", "off"], check=False)
        time.sleep(2)
        subprocess.run(["nmcli", "radio", "wifi", "on"], check=False)
        subprocess.run(["nmcli", "dev", "wifi", "rescan"], check=False)
        time.sleep(2)
        subprocess.run(["nmcli", "dev", "wifi", "list"], check=False)
        time.sleep(2)

        subprocess.run(
            [
                "sudo",
                "nmcli",
                "dev",
                "wifi",
                "connect",
                ssid,
                "password",
                password,
                "ifname",
                "wlan0",
                "name",
                ssid,
            ],
            check=True,
        )

        subprocess.run(
            ["sudo", "systemctl", "stop", "billy-wifi-setup.service"], check=False
        )

        time.sleep(5)
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "8.8.8.8"], stdout=subprocess.DEVNULL
        )
        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"❌ Connection failed: {e}")
        return False


def stop_hotspot_services():
    subprocess.call(["sudo", "systemctl", "stop", "hostapd"])
    subprocess.call(["sudo", "systemctl", "stop", "dnsmasq"])
    print("🛑 Stopped hotspot services")


def shutdown_flask_soon():
    # Delay shutdown so user sees message
    def delayed_exit():
        time.sleep(3)
        print("🌀 Shutting down Flask app...")
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()

    import threading

    threading.Thread(target=delayed_exit, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
