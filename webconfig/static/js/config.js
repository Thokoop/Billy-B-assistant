// ===================== LOGS =====================

let autoScrollEnabled = false;

async function fetchLogs() {
    const res = await fetch("/logs");
    const data = await res.json();
    const logOutput = document.getElementById("log-output");
    const logContainer = document.getElementById("log-container");

    logOutput.textContent = data.logs || "No logs found.";

    if (autoScrollEnabled) {
        requestAnimationFrame(() => {
            logContainer.scrollTop = logContainer.scrollHeight;
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Element references
    const elements = {
        logOutput: document.getElementById("log-output"),
        logContainer: document.getElementById("log-container"),
        toggleFullscreenBtn: document.getElementById("toggle-fullscreen-btn"),
        scrollBtn: document.getElementById("scroll-bottom-btn"),
        scrollBtnFullscreen: document.getElementById("scroll-bottom-btn-fullscreen"),
        logOverlay: document.getElementById("log-overlay"),
        body: document.body,
        toggleBtn: document.getElementById("toggle-log-btn"),
        logPanel: document.getElementById("log-panel"),
    };

    let isHidden = true;

    // Toggle log visibility
    function toggleLogPanel() {
        isHidden = !isHidden;
        elements.logPanel.classList.toggle("hidden", isHidden);
        elements.toggleBtn.textContent = isHidden ? "Show Debug" : "Hide Debug";
    }

    // Fullscreen mode using class toggle
    function toggleFullscreenLog() {
        const container = document.getElementById("log-container");
        const icon = document.getElementById("fullscreen-icon");

        const isFullscreen = container.classList.toggle("log-fullscreen");
        icon.textContent = isFullscreen ? "fullscreen_exit" : "fullscreen";
    }

    // Auto-scroll toggle
    function toggleAutoScroll() {
        autoScrollEnabled = !autoScrollEnabled;
        elements.scrollBtn.classList.toggle("bg-cyan-500", autoScrollEnabled);
        elements.scrollBtn.classList.toggle("bg-zinc-800", !autoScrollEnabled);
        elements.scrollBtn.title = autoScrollEnabled ? "Auto-scroll ON" : "Auto-scroll OFF";

        if (autoScrollEnabled) {
            elements.logOutput.scrollTop = elements.logOutput.scrollHeight;
        }
    }

    // Event bindings
    elements.toggleBtn.addEventListener("click", toggleLogPanel);
    elements.toggleFullscreenBtn.addEventListener("click", toggleFullscreenLog);
    elements.scrollBtn.addEventListener("click", toggleAutoScroll);
});

// ===================== SERVICE STATUS =====================

async function fetchStatus() {
    const res = await fetch("/service/status");
    const data = await res.json();
    updateServiceStatusUI(data.status);
}

function updateServiceStatusUI(status) {
    const statusEl = document.getElementById("service-status");
    const controlsEl = document.getElementById("service-controls");

    // Set status text
    statusEl.textContent = `(${status})`;

    // Reset previous color classes
    statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");

    // Add color based on status
    if (status === "active") {
        statusEl.classList.add("text-emerald-500");
    } else if (status === "inactive") {
        statusEl.classList.add("text-amber-500");
    } else if (status === "failed") {
        statusEl.classList.add("text-rose-500");
    }

    // Clear and repopulate controls
    controlsEl.innerHTML = "";

    const createButton = (label, action, color) => {
        const btn = document.createElement("button");
        btn.textContent = label;
        btn.className = `bg-${color}-500 hover:bg-${color}-600 text-black font-semibold py-1 px-3 rounded`;
        btn.onclick = () => handleServiceAction(action);
        return btn;
    };

    if (status === "inactive" || status === "failed") {
        controlsEl.appendChild(createButton("Start", "start", "emerald"));
    } else if (status === "active") {
        controlsEl.appendChild(createButton("Restart", "restart", "amber"));
        controlsEl.appendChild(createButton("Stop", "stop", "rose"));
    } else {
        controlsEl.textContent = "Unknown status.";
    }
}

async function handleServiceAction(action) {
    if(action == "restart") {
        const statusEl = document.getElementById("service-status");
        statusEl.textContent = `restarting`;
        statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");
        statusEl.classList.add("text-amber-500");
    }
    await fetch(`/service/${action}`);
    fetchStatus();
    fetchLogs();
}

// ===================== SETTINGS FORM =====================

function handleSettingsSave() {
    document.getElementById("config-form").addEventListener("submit", async function (e) {
        e.preventDefault();

        const res = await fetch("/service/status");
        const { status: wasActive } = await res.json();

        const formData = new FormData(this);
        const payload = Object.fromEntries(formData.entries());

        await fetch("/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        showNotification("Settings saved", "success");

        if (res.ok) {
            await setupDeviceControls();
        } else {
            alert("Failed to save settings.");
        }

        if (wasActive === "active") {
            await fetch("/service/restart");
            showNotification("Settings saved – service restarted", "success");
            fetchStatus();
        }
    });
}

// ===================== PERSONA FORM =====================

function addBackstoryField(key = "", value = "") {
    const wrapper = document.createElement("div");
    wrapper.className = "flex items-center space-x-2";

    const keyInput = Object.assign(document.createElement("input"), {
        type: "text",
        value: key,
        placeholder: "Key",
        className: "w-1/3 p-1 bg-zinc-800 text-white rounded"
    });

    const valInput = Object.assign(document.createElement("input"), {
        type: "text",
        value: value,
        placeholder: "Value",
        className: "flex-1 p-1 bg-zinc-800 text-white rounded"
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "text-red-400 text-xl";
    removeBtn.innerHTML = "&minus;";
    removeBtn.onclick = () => wrapper.remove();

    wrapper.append(keyInput, valInput, removeBtn);
    document.getElementById("backstory-fields").appendChild(wrapper);
}

async function loadPersona() {
    const res = await fetch("/persona");
    const data = await res.json();

    renderPersonalitySliders(data.PERSONALITY);
    renderBackstoryFields(data.BACKSTORY);
    document.getElementById("meta-text").value = data.META || "";
}

function renderPersonalitySliders(personality) {
    const container = document.getElementById("personality-sliders");
    container.innerHTML = "";

    for (const [key, value] of Object.entries(personality)) {
        const wrapper = document.createElement("div");
        wrapper.className = "flex items-center space-x-4";

        const label = document.createElement("label");
        label.className = "w-32 font-semibold text-sm";
        label.textContent = key;
        label.for = key;

        const input = Object.assign(document.createElement("input"), {
            type: "range",
            name: key,
            min: 0,
            max: 100,
            value,
            className: "flex-1"
        });

        const output = document.createElement("span");
        output.className = "w-10 text-sm text-zinc-400 text-right";
        output.textContent = value;

        input.addEventListener("input", () => {
            output.textContent = input.value;
        });

        wrapper.append(label, input, output);
        container.appendChild(wrapper);
    }
}

function renderBackstoryFields(backstory) {
    const container = document.getElementById("backstory-fields");
    container.innerHTML = "";
    Object.entries(backstory).forEach(([k, v]) => addBackstoryField(k, v));
}

function handlePersonaSave() {
    document.getElementById("persona-form").addEventListener("submit", async (e) => {
        e.preventDefault();

        const res = await fetch("/service/status");
        const { status: wasActive } = await res.json();

        const personality = {};
        document.querySelectorAll("#personality-sliders input").forEach((input) => {
            personality[input.name] = parseInt(input.value, 10);
        });

        const backstory = {};
        document.querySelectorAll("#backstory-fields > div").forEach((row) => {
            const [keyInput, valInput] = row.querySelectorAll("input");
            if (keyInput.value.trim() !== "") {
                backstory[keyInput.value.trim()] = valInput.value.trim();
            }
        });

        const meta = document.getElementById("meta-text").value.trim();

        await fetch("/persona", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ PERSONALITY: personality, BACKSTORY: backstory, META: meta })
        });

        showNotification("Persona saved", "success");

        if (wasActive === "active") {
            await fetch("/service/restart");
            showNotification("Persona saved – service restarted", "success");
            fetchStatus();
        }
    });
}

// ===================== UI =====================

function showNotification(message, type = "info", duration = 2500) {
    const bar = document.getElementById("notification");
    bar.textContent = message;

    // Remove old type classes
    bar.classList.remove("hidden", "opacity-0", "bg-cyan-500/80", "bg-emerald-500/80", "bg-amber-500/80", "bg-rose-500/80");

    // Add the new type class
    const typeClass = {
        info: "bg-cyan-500/80",
        success: "bg-emerald-500/80",
        warning: "bg-amber-500/80",
        error: "bg-rose-500/80",
    }[type] || "bg-cyan-500/80";

    bar.classList.add(typeClass, "opacity-100");

    // Hide after duration
    setTimeout(() => {
        bar.classList.remove("opacity-100");
        bar.classList.add("opacity-0");
        setTimeout(() => bar.classList.add("hidden"), 300);
    }, duration);
}

function toggleInputVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(`${inputId}_icon`);
    const isHidden = input.type === "password";

    input.type = isHidden ? "text" : "password";
    icon.textContent = isHidden ? "visibility_off" : "visibility";
}

fetch("/version")
    .then(res => res.json())
    .then(data => {
        document.getElementById("current-version").textContent = `${data.current}`;

        if (data.update_available) {
            const latestSpan = document.getElementById("latest-version");
            latestSpan.textContent = `Update to: ${data.latest}`;
            latestSpan.classList.remove("hidden");
            document.getElementById("update-btn").classList.remove("hidden");
        }
    })
    .catch(err => {
        console.error("Failed to load version info", err);
    });
document.getElementById("update-btn").addEventListener("click", () => {
    if (!confirm("Are you sure you want to update Billy to the latest version?")) return;

    fetch("/update", { method: "POST" })
        .then(res => res.json())
        .then(data => {
            showNotification(data.message || "Update triggered");

            let attempts = 0;
            const maxAttempts = 24; // 5s × 24 = 120s

            const checkForUpdate = async () => {
                try {
                    const res = await fetch("/version");
                    const { current, latest } = await res.json();

                    if (current === latest) {
                        showNotification("Update complete. Reloading...", "info");
                        setTimeout(() => location.reload(), 1500);
                        return;
                    }
                } catch (err) {
                    console.error("Version check failed:", err);
                }

                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkForUpdate, 5000);
                } else {
                    showNotification("Update timed out after 2 minutes.");
                }
            };

            setTimeout(checkForUpdate, 5000); // Start first check after 5s
        })
        .catch(err => {
            console.error("Failed to start update:", err);
            showNotification("Failed to start update", "error");
        });
});

// ===================== AUDIO =====================

let micCheckSource = null;

document.getElementById("mic-check-btn").addEventListener("click", toggleMicCheck);

document.getElementById("speaker-check-btn").addEventListener("click", async () => {
    try {
        const res = await fetch("/service/status");
        const { status } = await res.json();

        if (status === "active") {
            showNotification("⚠️ Please stop the Billy service before running speaker test.", "warning");
            return;
        }

        await fetch("/speaker-test", { method: "POST" });
        showNotification("Speaker test triggered");

    } catch (err) {
        console.error("Failed to trigger speaker test:", err);
        showNotification("Failed to trigger speaker test", "error");
    }
});

async function toggleMicCheck() {
    const btn = document.getElementById("mic-check-btn");
    const isActive = btn.classList.contains("bg-emerald-600");

    if (isActive) {
        stopMicCheck();
        btn.classList.remove("bg-emerald-600");
        btn.classList.add("bg-zinc-800");
        showNotification("Mic check stopped");
    } else {
        try {
            const res = await fetch("/service/status");
            const { status } = await res.json();

            if (status === "active") {
                showNotification("⚠️ Please stop the Billy service before running mic check.", "warning");
                return;
            }

            startMicCheck();
            btn.classList.remove("bg-zinc-800");
            btn.classList.add("bg-emerald-600");
            showNotification("Mic check started");
        } catch (err) {
            console.error("Failed to toggle mic check:", err);
            showNotification("Mic check failed", "error");
        }
    }
}

function stopMicCheck() {
    micCheckSource.close();
    fetch("/mic-check/stop");
    micCheckSource = null;

    updateMicBar(0);
}

function startMicCheck() {
    let maxRms = 0;
    const SCALING_FACTOR = 32768;

    micCheckSource = new EventSource("/mic-check");

    micCheckSource.onmessage = (e) => {
        let data;
        try {
            data = JSON.parse(e.data);
        } catch (err) {
            console.error("Invalid JSON from /mic-check:", e.data);
            return;
        }

        if (data.error) {
            console.error("Mic check error:", data.error);
            return;
        }

        const rms = data.rms * SCALING_FACTOR;
        const threshold = data.threshold; // already a scaled int like 300, 500, etc.
        maxRms = Math.max(maxRms, rms);

        const percent = Math.min((rms / threshold) * 100, 100); // percent of threshold
        const thresholdPercent = Math.min((threshold / SCALING_FACTOR) * 100, 100);

        updateMicBar(percent, thresholdPercent);
    };

    micCheckSource.onerror = () => {
        console.error("Mic check connection error.");
        stopMicCheck();
    };
}

function updateMicBar(percentage, thresholdPercent = 0) {
    const bar = document.getElementById("mic-level-bar");
    bar.style.width = `${percentage}%`;

    bar.classList.toggle("bg-zinc-500", percentage < thresholdPercent);
    bar.classList.toggle("bg-emerald-500", percentage < 70);
    bar.classList.toggle("bg-amber-500", percentage >= 70 && percentage < 90);
    bar.classList.toggle("bg-red-500", percentage >= 90);
}

async function loadMicGain() {
    const label = document.getElementById("mic-gain-value");
    const slider = document.getElementById("mic-gain");

    try {
        const res = await fetch("/mic-gain");
        const data = await res.json();
        if (data.gain !== undefined) {
            label.textContent = data.gain;
            slider.value = data.gain;
        } else {
            label.textContent = "Unavailable";
        }
    } catch (err) {
        label.textContent = "Error";
    }
}

document.getElementById("mic-gain").addEventListener("change", async () => {
    const value = parseInt(document.getElementById("mic-gain").value, 10);
    await fetch("/mic-gain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value })
    });
    document.getElementById("mic-gain-value").textContent = value;
});

let micBar = document.getElementById("mic-bar-container");
let thresholdLine = document.getElementById("threshold-line");
let silenceThresholdInput = document.getElementById("SILENCE_THRESHOLD");

let dragging = false;

thresholdLine.addEventListener("mousedown", (e) => {
    dragging = true;
    e.preventDefault();
});

document.addEventListener("mousemove", (e) => {
    if (!dragging) return;

    const rect = micBar.getBoundingClientRect();
    if (rect.width === 0) return;

    let offsetX = e.clientX - rect.left;
    offsetX = Math.max(0, Math.min(offsetX, rect.width));

    const percent = offsetX / rect.width;
    const scaledThreshold = Math.round(percent * 32768); // scale and round

    thresholdLine.style.left = `${percent * 100}%`;
    silenceThresholdInput.value = scaledThreshold; // set int value
});

document.addEventListener("mouseup", () => {
    dragging = false;
});

// Initialize threshold line position on load
window.addEventListener("load", () => {
    const threshold = parseInt(silenceThresholdInput.value || "1000", 10); // fallback to safe int
    thresholdLine.style.left = `${(threshold / 32768) * 100}%`;
});

const speakerSlider = document.getElementById("speaker-volume");

// Load current volume
fetch("/volume")
    .then(res => res.json())
    .then(data => {
        if (data.volume !== undefined) {
            speakerSlider.value = data.volume;
        }
    });

// Set new volume on slider change
let volumeDebounceTimeout;

speakerSlider.addEventListener("input", () => {
    clearTimeout(volumeDebounceTimeout); // cancel previous timer

    volumeDebounceTimeout = setTimeout(() => {
        fetch("/volume", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ volume: parseInt(speakerSlider.value) })
        }).catch(err => console.error("Failed to set speaker volume:", err));
    }, 500); // wait 500ms after last input
});

async function updateDeviceLabels() {
    try {
        const res = await fetch("/device-info");
        const data = await res.json();

        const updateParentClass = (id, value) => {
            const el = document.getElementById(id);
            if (el && el.parentElement) {
                el.textContent = value;
                el.parentElement.classList.add("text-emerald-500");
            }
        };

        updateParentClass("mic-label", data.mic);
        updateParentClass("speaker-label", data.speaker);

    } catch (error) {
        console.error("Failed to fetch device info:", error);
    }
}

// ===================== INITIALIZE =====================

document.addEventListener("DOMContentLoaded", () => {
    fetchLogs();
    fetchStatus();
    setInterval(fetchLogs, 5000);
    setInterval(fetchStatus, 10000);
    updateDeviceLabels();
    loadPersona();
    loadMicGain();
    handleSettingsSave();
    handlePersonaSave();
});