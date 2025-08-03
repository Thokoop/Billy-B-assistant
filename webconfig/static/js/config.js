// ===================== Header Secondary Actions =====================

const LogPanel = (() => {
    let autoScrollEnabled = false;
    let isLogHidden = true;
    let isEnvHidden = true;

    // Reboot Billy
    const rebootBilly = async () => {
        if (!confirm("Are you sure you want to reboot Billy? This will reboot the whole system.")) return;
        try {
            const res = await fetch('/reboot', {method: 'POST'});
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Billy is rebooting!", "success");
                setTimeout(() => {
                    location.reload();
                }, 15000);
            }
            else {
                showNotification(data.error || "Reboot failed", "error");
            }
        } catch (err) {
            console.error("Failed to reboot Billy:", err);
            showNotification("Failed to reboot Billy", "error");
        }
    };

    // Shutdown Billy
    const shutdownBilly = async () => {
        if (!confirm("Are you sure you want to shutdown Billy? This will completely shutdown the system!")) return;
        try {
            const res = await fetch('/shutdown', {method: 'POST'});
            const data = await res.json();
            if (data.status === "ok") {
                showNotification("Billy is shutting down!", "success");
                setTimeout(() => {
                    location.reload();
                }, 3000);
            }
            else {
                showNotification(data.error || "Shutdown failed", "error");
            }
        } catch (err) {
            console.error("Failed to shutdown Billy:", err);
            showNotification("Failed to shutdown Billy", "error");
        }
    };

    // Fetch logs and update UI
    const fetchLogs = async () => {
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
    };

    // Toggle log panel visibility
    const toggleLogPanel = () => {
        isLogHidden = !isLogHidden;
        elements.logPanel.classList.toggle("hidden", isLogHidden);
        elements.toggleBtn.classList.toggle("bg-cyan-500", !isLogHidden);
        elements.toggleBtn.classList.toggle("bg-zinc-700", isLogHidden);
    };

    // Toggle .env editor visibility and fetch content if showing
    const toggleEnvPanel = () => {
        isEnvHidden = !isEnvHidden;
        elements.envPanel.classList.toggle("hidden", isEnvHidden);
        elements.toggleEnvBtn.classList.toggle("bg-amber-500", !isEnvHidden);
        elements.toggleEnvBtn.classList.toggle("bg-zinc-700", isEnvHidden);

        if (!isEnvHidden) {
            fetch('/get-env')
                .then(res => res.text())
                .then(text => elements.envTextarea.value = text.trim())
                .catch(() => showNotification("An error occurred while loading .env", "error"));
        }
    };

    const toggleMotion = () => {
        const btn = elements.toggleMotionBtn;
        const icon = btn.querySelector(".material-icons");

        btn.classList.toggle("bg-zinc-700");
        document.documentElement.classList.toggle("reduce-motion");

        const isReduced = document.documentElement.classList.contains("reduce-motion");
        localStorage.setItem("reduceMotion", isReduced ? "1" : "0");

        // Toggle icon
        if (icon) {
            icon.textContent = isReduced ? "blur_off" : "blur_on";
        }
    };

    // Fullscreen toggle
    const toggleFullscreenLog = () => {
        const icon = document.getElementById("fullscreen-icon");
        const isFullscreen = elements.logContainer.classList.toggle("log-fullscreen");
        icon.textContent = isFullscreen ? "fullscreen_exit" : "fullscreen";
    };

    // Toggle auto-scroll to bottom of log
    const toggleAutoScroll = () => {
        autoScrollEnabled = !autoScrollEnabled;
        elements.scrollBtn.classList.toggle("bg-cyan-500", autoScrollEnabled);
        elements.scrollBtn.classList.toggle("bg-zinc-800", !autoScrollEnabled);
        elements.scrollBtn.title = autoScrollEnabled ? "Auto-scroll ON" : "Auto-scroll OFF";

        if (autoScrollEnabled) {
            elements.logOutput.scrollTop = elements.logOutput.scrollHeight;
        }
    };

    // Save .env file and optionally restart service
    const saveEnv = async () => {
        if (!confirm("Are you sure you want to overwrite the .env file? This may affect how Billy runs.")) return;

        try {
            const res = await fetch('/save-env', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: elements.envTextarea.value})
            });
            const data = await res.json();

            if (data.status === "ok") {
                fetch('/restart', {method: 'POST'})
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === "ok") {
                            showNotification(".env saved. Restarting", "success");
                            setTimeout(() => location.reload(), 3000);
                        } else {
                            showNotification(data.error || "Restart failed", "error");
                        }
                    })
                    .catch(err => showNotification(err.message, "error"));
            } else {
                showNotification(data.error || "Unknown error", "error");
            }
        } catch (err) {
            showNotification(err.message, "error");
        }
    };

    // Cache DOM references after DOMContentLoaded
    let elements = {};
    const bindUI = () => {
        elements = {
            logOutput: document.getElementById("log-output"),
            logContainer: document.getElementById("log-container"),
            toggleFullscreenBtn: document.getElementById("toggle-fullscreen-btn"),
            scrollBtn: document.getElementById("scroll-bottom-btn"),
            toggleBtn: document.getElementById("toggle-log-btn"),
            logPanel: document.getElementById("log-panel"),
            toggleEnvBtn: document.getElementById("toggle-env-btn"),
            envPanel: document.getElementById("env-panel"),
            envTextarea: document.getElementById("env-textarea"),
            saveEnvBtn: document.getElementById("save-env-btn"),
            toggleMotionBtn: document.getElementById("toggle-motion-btn"),
            rebootBillyBtn: document.getElementById("reboot-billy-btn"),
            shutdownBillyBtn: document.getElementById("shutdown-billy-btn"),
        };

        elements.toggleBtn.addEventListener("click", toggleLogPanel);
        elements.toggleFullscreenBtn.addEventListener("click", toggleFullscreenLog);
        elements.scrollBtn.addEventListener("click", toggleAutoScroll);
        elements.toggleEnvBtn.addEventListener("click", toggleEnvPanel);
        elements.toggleMotionBtn.addEventListener("click", toggleMotion);
        elements.saveEnvBtn.addEventListener("click", saveEnv);
        elements.rebootBillyBtn.addEventListener("click", rebootBilly);
        elements.shutdownBillyBtn.addEventListener("click", shutdownBilly);

        if (localStorage.getItem("reduceMotion") === "1") {
            document.documentElement.classList.add("reduce-motion");

            const btn = elements.toggleMotionBtn;
            const icon = btn.querySelector(".material-icons");
            btn.classList.remove("bg-zinc-700");

            if (icon) {
                icon.textContent = "blur_off";
            }
        }
    };

    return {fetchLogs, bindUI};
})();

// ===================== SERVICE STATUS =====================

const ServiceStatus = (() => {
    const fetchStatus = async () => {
        const res = await fetch("/service/status");
        const data = await res.json();
        updateServiceStatusUI(data.status);
    };

    const updateServiceStatusUI = (status) => {
        const statusEl = document.getElementById("service-status");
        const controlsEl = document.getElementById("service-controls");
        statusEl.textContent = `(${status})`;
        statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");

        if (status === "active") {
            statusEl.classList.add("text-emerald-500");
        } else if (status === "inactive") {
            statusEl.classList.add("text-amber-500");
        } else if (status === "failed") {
            statusEl.classList.add("text-rose-500");
        }

        controlsEl.innerHTML = "";
        const createButton = (label, action, color, iconName) => {
            const btn = document.createElement("button");
            btn.className = `flex items-center gap-1 bg-${color}-500 hover:bg-${color}-400 text-zinc-800 font-semibold py-1 px-2 rounded`;

            const icon = document.createElement("i");
            icon.className = "material-icons";
            icon.textContent = iconName;
            btn.appendChild(icon);

            const labelSpan = document.createElement("span");
            labelSpan.className = "hidden md:inline";
            labelSpan.textContent = label;
            btn.appendChild(labelSpan);

            btn.onclick = () => handleServiceAction(action);
            return btn;
        };
        if (status === "inactive" || status === "failed") {
            controlsEl.appendChild(createButton("Start", "start", "emerald", "play_arrow"));
        } else if (status === "active") {
            controlsEl.appendChild(createButton("Restart", "restart", "amber", "restart_alt"));
            controlsEl.appendChild(createButton("Stop", "stop", "rose", "stop"));
        } else {
            controlsEl.textContent = "Unknown status.";
        }
    };

    const handleServiceAction = async (action) => {
        const statusEl = document.getElementById("service-status");
        const statusMap = {
            restart: {text: "restarting", color: "text-amber-500"},
            stop: {text: "stopping", color: "text-rose-500"},
            start: {text: "starting", color: "text-emerald-500"}
        };

        if (statusMap[action]) {
            const {text, color} = statusMap[action];
            statusEl.textContent = text;
            statusEl.classList.remove("text-emerald-500", "text-amber-500", "text-rose-500");
            statusEl.classList.add(color);
        }
        try {
            await fetch(`/service/${action}`);
        } catch (err) {
            console.error(`Failed to ${action} service:`, err);
        }
        fetchStatus();
        LogPanel.fetchLogs();
    };

    return {fetchStatus, updateServiceStatusUI};
})();

// ===================== SETTINGS FORM =====================

const SettingsForm = (() => {
    const handleSettingsSave = () => {
        document.getElementById("config-form").addEventListener("submit", async function (e) {
            e.preventDefault();

            const resStatus = await fetch("/service/status");
            const {status: wasActive} = await resStatus.json();

            const formData = new FormData(this);
            const payload = Object.fromEntries(formData.entries());

            const flaskPortInput = document.getElementById("FLASK_PORT");
            const oldPort = parseInt(flaskPortInput.getAttribute("data-original")) || 80;
            const newPort = parseInt(payload["FLASK_PORT"] || "80");

            const hostnameInput = document.getElementById("hostname");
            const oldHostname = (hostnameInput.getAttribute("data-original") || hostnameInput.defaultValue || "").trim();
            const newHostname = (formData.get("hostname") || "").trim();

            let hostnameChanged = false;

            // Save config (.env)
            const saveResponse = await fetch("/save", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
            const saveResult = await saveResponse.json();
            let portChanged = saveResult.port_changed || (oldPort !== newPort);

            // Only update hostname if it actually changed
            if (newHostname && newHostname !== oldHostname) {
                const hostResponse = await fetch("/hostname", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({hostname: newHostname})
                });
                const hostResult = await hostResponse.json();
                if (hostResult.hostname) {
                    hostnameChanged = true;
                    showNotification(`Hostname updated to ${hostResult.hostname}.local`, "success", 5000);
                }
            }

            if (wasActive === "active") {
                await fetch("/service/restart");
                showNotification("Settings saved – Billy restarted", "success");
            } else {
                showNotification("Settings saved", "success");
            }

            if (portChanged || hostnameChanged) {
                const targetHost = hostnameChanged ? `${newHostname}.local` : window.location.hostname;
                const targetPort = portChanged ? newPort : (window.location.port || 80);

                showNotification(`Redirecting to http://${targetHost}:${targetPort}/...`, "warning", 5000);
                setTimeout(() => {
                    window.location.href = `http://${targetHost}:${targetPort}/`;
                }, 3000);
            }
        });
    };

    // Set hostname field from server
    fetch('/hostname')
        .then(res => res.json())
        .then(data => {
            if (data.hostname) {
                const input = document.getElementById('hostname');
                input.value = data.hostname;
                input.setAttribute('data-original', data.hostname);
            }
        });

    // Set original port attribute for change detection
    const flaskPortInput = document.getElementById("FLASK_PORT");
    if (flaskPortInput) {
        flaskPortInput.setAttribute("data-original", flaskPortInput.value);
    }

    return {handleSettingsSave};
})();

// ===================== PERSONA FORM =====================

const PersonaForm = (() => {
    const addBackstoryField = (key = "", value = "") => {
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
        removeBtn.className = "text-rose-500 hover:text-rose-400 cursor-pointer";
        const icon = document.createElement("span");
        icon.className = "material-icons align-middle";
        icon.textContent = "remove_circle_outline";
        removeBtn.appendChild(icon);
        removeBtn.onclick = () => wrapper.remove();

        wrapper.append(keyInput, valInput, removeBtn);
        document.getElementById("backstory-fields").appendChild(wrapper);
    };

    const renderPersonalitySliders = (personality) => {
        const container = document.getElementById("personality-sliders");
        container.innerHTML = "";

        for (const [key, value] of Object.entries(personality)) {
            const wrapper = document.createElement("div");
            wrapper.className = "flex gap-2 space-y-1";

            // Label column
            const label = document.createElement("div");
            label.className = "flex w-36 justify-between items-center text-sm text-slate-300 font-semibold";
            label.innerHTML = `<span>${key}</span>`;

            // Bar container
            const barContainer = document.createElement("div");
            barContainer.className = "relative w-full rounded-full bg-zinc-700 overflow-hidden cursor-pointer";
            barContainer.style.userSelect = "none";

            // Fill bar
            const fillBar = document.createElement("div");
            fillBar.className = "absolute left-0 top-0 h-full bg-emerald-500 transition-all duration-100";
            fillBar.style.width = `${value}%`;
            fillBar.dataset.fillFor = key;

            barContainer.appendChild(fillBar);

            // Output value
            const valueLabel = document.createElement("span");
            valueLabel.id = `${key}-value`;
            valueLabel.className = "text-zinc-400 w-4";
            valueLabel.textContent = value;

            // Drag interaction
            let isDragging = false;

            const updateValue = (e) => {
                const rect = barContainer.getBoundingClientRect();
                const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
                const newVal = Math.round(percent * 100);
                fillBar.style.width = `${newVal}%`;
                valueLabel.textContent = newVal;
                fillBar.setAttribute("data-value", newVal);
            };

            barContainer.addEventListener("mousedown", (e) => {
                isDragging = true;
                updateValue(e);
            });

            document.addEventListener("mousemove", (e) => {
                if (isDragging) updateValue(e);
            });

            document.addEventListener("mouseup", () => {
                isDragging = false;
            });

            wrapper.appendChild(label);
            wrapper.appendChild(barContainer);
            wrapper.appendChild(valueLabel);

            container.appendChild(wrapper);
        }
    };

    function setupSlider(barId, fillId, inputId, min, max) {
        const bar = document.getElementById(barId);
        const fill = document.getElementById(fillId);
        const input = document.getElementById(inputId);

        let isDragging = false;

        const updateUI = (val) => {
            const percent = ((val - min) / (max - min)) * 100;
            fill.style.width = `${percent}%`;
            fill.dataset.value = val;
        };

        const updateFromMouse = (e) => {
            const rect = bar.getBoundingClientRect();
            const percent = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
            const val = Math.round(min + percent * (max - min));
            input.value = val;
            input.dispatchEvent(new Event("input", {bubbles: true}));
            updateUI(val);
        };

        // Allow dragging
        bar.addEventListener("mousedown", (e) => {
            isDragging = true;
            updateFromMouse(e);
        });

        document.addEventListener("mousemove", (e) => {
            if (isDragging) updateFromMouse(e);
        });

        document.addEventListener("mouseup", () => {
            isDragging = false;
        });

        // Sync with input on load/change (just in case)
        input.addEventListener("input", () => updateUI(Number(input.value)));
        updateUI(Number(input.value));
    }

    setupSlider("mic-gain-bar", "mic-gain-fill", "mic-gain", 0, 16);
    setupSlider("speaker-volume-bar", "speaker-volume-fill",  "speaker-volume", 0, 100);

    const renderBackstoryFields = (backstory) => {
        const container = document.getElementById("backstory-fields");
        container.innerHTML = "";
        Object.entries(backstory).forEach(([k, v]) => addBackstoryField(k, v));
    };

    const loadPersona = async () => {
        const res = await fetch("/persona");
        const data = await res.json();
        renderPersonalitySliders(data.PERSONALITY);
        renderBackstoryFields(data.BACKSTORY);
        document.getElementById("meta-text").value = data.META || "";
    };

    const handlePersonaSave = () => {
        document.getElementById("persona-form").addEventListener("submit", async (e) => {
            e.preventDefault();

            const res = await fetch("/service/status");
            const {status: wasActive} = await res.json();

            const personality = {};
            document.querySelectorAll("#personality-sliders div[data-fill-for]").forEach((bar) => {
                const trait = bar.dataset.fillFor;
                personality[trait] = parseInt(bar.style.width);
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
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({PERSONALITY: personality, BACKSTORY: backstory, META: meta})
            });

            showNotification("Persona saved", "success");

            if (wasActive === "active") {
                await fetch("/service/restart");
                showNotification("Persona saved – service restarted", "success");
                ServiceStatus.fetchStatus();
            }
        });
    };

    return {addBackstoryField, loadPersona, handlePersonaSave};
})();

// ===================== UI HELPERS =====================

function showNotification(message, type = "info", duration = 2500) {
    const bar = document.getElementById("notification");
    bar.textContent = message;
    bar.classList.remove("hidden", "opacity-0", "bg-cyan-500/80", "bg-emerald-500/80", "bg-amber-500/80", "bg-rose-500/80");
    const typeClass = {
        info: "bg-cyan-500/80",
        success: "bg-emerald-500/80",
        warning: "bg-amber-500/80",
        error: "bg-rose-500/80",
    }[type] || "bg-cyan-500/80";
    bar.classList.add(typeClass, "opacity-100");
    setTimeout(() => {
        bar.classList.remove("opacity-100");
        bar.classList.add("opacity-0");
        setTimeout(() => bar.classList.add("hidden"), 300);
    }, duration);
}

// Toggle password input visibility
function toggleInputVisibility(inputId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(`${inputId}_icon`);
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    icon.textContent = isHidden ? "visibility_off" : "visibility";
}

function toggleDropdown(btn) {
    // Close all other dropdowns first
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        // Only close menus not related to this button
        if (!menu.classList.contains('hidden') && !menu.parentElement.contains(btn)) {
            menu.classList.add('hidden');
            const arrow = menu.parentElement.querySelector('.dropdown-toggle .material-icons');
            if (arrow) arrow.classList.remove('rotate-180');
        }
    });

    // Find this button's dropdown menu (assumes menu is sibling or child)
    let dropdown = btn.closest('.relative').querySelector('.dropdown-menu');
    if (!dropdown) return;

    dropdown.classList.toggle('hidden');

    // Toggle arrow rotation
    const arrow = btn.querySelector('.material-icons');
    if (arrow) arrow.classList.toggle('rotate-180');
}

function toggleTooltip(el) {
    el.classList.toggle("text-cyan-400")
    const container = el.closest("label")?.parentElement;
    if (!container) return;

    const tooltip = container.querySelector("[data-tooltip]");
    if (tooltip) {
        const visible = tooltip.getAttribute("data-visible") === "true";
        tooltip.setAttribute("data-visible", visible ? "false" : "true");
    }
}


// Close on click outside
document.addEventListener('click', (e) => {
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        // If the click is outside the .relative container
        if (!menu.classList.contains('hidden') && !menu.closest('.relative').contains(e.target)) {
            menu.classList.add('hidden');
            const arrow = menu.parentElement.querySelector('.dropdown-toggle .material-icons');
            if (arrow) arrow.classList.remove('rotate-180');
        }
    });
});

// ===================== VERSION & UPDATE =====================

(() => {
    fetch("/version")
        .then(res => res.json())
        .then(data => {
            document.getElementById("current-version").textContent = `${data.current}`;
            if (data.update_available) {
                const latestSpan = document.getElementById("latest-version");
                const updateBtn = document.getElementById("update-btn");
                latestSpan.textContent = `Update to: ${data.latest}`;
                latestSpan.classList.remove("hidden");
                updateBtn.classList.add('flex');
                updateBtn.classList.remove("hidden");
            }
        })
        .catch(err => {
            console.error("Failed to load version info", err);
        });

    document.getElementById("update-btn").addEventListener("click", () => {
        if (!confirm("Are you sure you want to update Billy to the latest version?")) return;
        fetch("/update", {method: "POST"})
            .then(res => res.json())
            .then(data => {
                showNotification(data.message || "Update started");
                let attempts = 0, maxAttempts = 24;
                const checkForUpdate = async () => {
                    try {
                        const res = await fetch("/version");
                        const data = await res.json();
                        if (data.update_available === false) {
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
                        showNotification("Update timed out after 2 minutes. Reloading");
                        setTimeout(() => location.reload(), 1500);
                    }
                };
                setTimeout(checkForUpdate, 5000);
            })
            .catch(err => {
                console.error("Failed to update:", err);
                showNotification("Failed to update", "error");
            });
    });
})();

// ===================== AUDIO =====================

const AudioPanel = (() => {
    let micCheckSource = null;

    const micCheckBtn = document.getElementById("mic-check-btn");
    micCheckBtn.addEventListener("click", toggleMicCheck);

    document.getElementById("speaker-check-btn").addEventListener("click", async () => {
        try {
            const res = await fetch("/service/status");
            const {status} = await res.json();
            if (status === "active") {
                showNotification("⚠️ Please stop the Billy service before running speaker test.", "warning");
                return;
            }
            await fetch("/speaker-test", {method: "POST"});
            showNotification("Speaker test triggered");
        } catch (err) {
            console.error("Failed to trigger speaker test:", err);
            showNotification("Failed to trigger speaker test", "error");
        }
    });

    async function toggleMicCheck() {
        const btn = micCheckBtn;
        const isActive = btn.classList.contains("bg-emerald-600");
        if (isActive) {
            stopMicCheck();
            btn.classList.remove("bg-emerald-600");
            btn.classList.add("bg-zinc-800");
            showNotification("Mic check stopped");
        } else {
            try {
                const res = await fetch("/service/status");
                const {status} = await res.json();
                if (status === "active") {
                    await fetch("/service/stop");
                    showNotification("Billy was stopped for mic check. You’ll need to start it again afterwards.", "warning");
                }
                startMicCheck();
                btn.classList.remove("bg-zinc-800");
                btn.classList.add("bg-emerald-600");
                if (status !== "active") {
                    showNotification("Mic check started");
                }
            } catch (err) {
                console.error("Failed to toggle mic check:", err);
                showNotification("Mic check failed", "error");
            }
        }
    }

    function stopMicCheck() {
        micCheckSource?.close();
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
            const threshold = data.threshold;
            maxRms = Math.max(maxRms, rms);
            const percent = Math.min((rms / threshold) * 100, 100);
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

    // Mic gain UI
    async function loadMicGain() {
        const label = document.getElementById("mic-gain-value");
        const slider = document.getElementById("mic-gain");
        const fill = document.getElementById("mic-gain-fill");

        try {
            const res = await fetch("/mic-gain");
            const data = await res.json();
            if (data.gain !== undefined) {
                slider.value = data.gain;
                label.textContent = data.gain;

                const percent = (data.gain / 16) * 100;
                fill.style.width = `${percent}%`;
                fill.dataset.value = data.gain;
            } else {
                label.textContent = "Unavailable";
            }
        } catch (err) {
            label.textContent = "Error";
        }
    }

    document.getElementById("mic-gain").addEventListener("input", async () => {
        const value = parseInt(document.getElementById("mic-gain").value, 10);
        await fetch("/mic-gain", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({value})
        });
        document.getElementById("mic-gain-value").textContent = value;
    });

    // Silence threshold drag interaction
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
        const scaledThreshold = Math.round(percent * 32768);
        thresholdLine.style.left = `${percent * 100}%`;
        silenceThresholdInput.value = scaledThreshold;
    });

    document.addEventListener("mouseup", () => {
        dragging = false;
    });

    window.addEventListener("load", () => {
        const threshold = parseInt(silenceThresholdInput.value || "1000", 10);
        thresholdLine.style.left = `${(threshold / 32768) * 100}%`;
    });

    // Speaker volume
    const speakerSlider = document.getElementById("speaker-volume");
    fetch("/volume")
        .then(res => res.json())
        .then(data => {
            if (data.volume !== undefined) {
                speakerSlider.value = data.volume;
                const fill = document.getElementById("speaker-volume-fill");
                const percent = (data.volume / 100) * 100;
                fill.style.width = `${percent}%`;
                fill.dataset.value = data.volume;
            }
        });
    let volumeDebounceTimeout;

    speakerSlider.addEventListener("input", () => {
        clearTimeout(volumeDebounceTimeout);
        volumeDebounceTimeout = setTimeout(() => {
            fetch("/volume", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({volume: parseInt(speakerSlider.value)})
            }).catch(err => console.error("Failed to set speaker volume:", err));
        }, 500);
    });

    // Device labels
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

    return {loadMicGain, updateDeviceLabels};
})();

// ===================== MOTOR TEST PANEL =====================

const MotorPanel = (() => {
    function sendMotorTest(motor) {
        fetch("/test-motor", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({motor})
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    showNotification("Motor error: " + data.error, "error", 4000);
                } else {
                    showNotification(`Tested ${motor}`, "success", 1500);
                    if (data.service_was_active) {
                        showNotification(
                            "Billy was stopped for hardware test. Please restart Billy again when done.",
                            "warning",
                            7000
                        );
                        ServiceStatus.fetchStatus();
                    }
                }
            })
            .catch(err => showNotification("Motor test failed: " + err, "error"));
    }

    // Attach events after DOM loaded
    function bindUI() {
        ["mouth", "head", "tail"].forEach(motor => {
            const btn = document.getElementById(`test-${motor}-btn`);
            if (btn) {
                btn.addEventListener("click", function () {
                    sendMotorTest(motor);
                });
            }
        });
    }

    return {bindUI};
})();

// ===================== COLLAPSIBLE SECTIONS =====================

const Sections = (() => {
    function collapsible() {
        document.querySelectorAll('.collapsible-section').forEach(section => {
            const header = section.querySelector('h3');
            if (!header) return;

            // Add icon if not present
            let icon = header.querySelector('.material-icons');
            if (!icon) {
                icon = document.createElement('span');
                icon.className = 'material-icons transition-transform duration-200 ml-2 rotate-0';
                icon.textContent = 'expand_more';
                header.appendChild(icon);
            } else {
                icon.classList.add('transition-transform', 'duration-200', 'ml-2');
                icon.classList.add('rotate-0');
            }

            // Restore state from localStorage
            const id = section.id;
            const collapsed = localStorage.getItem('collapse_' + id) === 'closed';

            icon.classList.toggle('rotate-180', !collapsed);
            icon.classList.toggle('rotate-0', collapsed);
            header.classList.toggle('mb-4', !collapsed);

            [...section.children].forEach(child => {
                if (child !== header) child.classList.toggle('hidden', collapsed);
            });

            // Click to toggle
            header.addEventListener('click', () => {
                const collapsed = section.classList.toggle('collapsed');
                [...section.children].forEach(child => {
                    if (child !== header) child.classList.toggle('hidden', collapsed);
                });
                icon.classList.toggle('rotate-180', !collapsed);
                icon.classList.toggle('rotate-0', collapsed);

                // Toggle mb-4 on h3 only when expanded
                header.classList.toggle('mb-4', !collapsed);

                localStorage.setItem('collapse_' + id, collapsed ? 'closed' : 'open');
            });
        });
    }

    return {collapsible};
})();

// ===================== IMPORT / EXPORT =====================

function exportSettings() {
    fetch('/get-env').then(res => res.text()).then(text => {
        const blob = new Blob([text], {type: "application/octet-stream"});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "billy.env";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}

function importSettings(input) {
    const file = input.files[0];
    if (!file) return;
    if (!file.name.endsWith('.env')) {
        showNotification("Only .env files are allowed.", "error");
        return;
    }
    const reader = new FileReader();
    reader.onload = function (e) {
        fetch('/save-env', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content: e.target.result})
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === "ok") {
                    showNotification("Settings imported. Restarting...", "success");
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showNotification(data.error || "Failed to import settings.", "error");
                }
            });
    };
    reader.readAsText(file);
}

function exportPersona() {
    const a = document.createElement('a');
    a.href = '/persona/export';
    a.download = 'persona.ini';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function importPersona(input) {
    const file = input.files[0];
    if (!file) return;
    if (!file.name.endsWith('.ini')) {
        showNotification("Only .ini files are allowed.", "error");
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    fetch('/persona/import', {
        method: 'POST',
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === "ok") {
                showNotification("Persona imported. Restarting...", "success");
                setTimeout(() => location.reload(), 2000);
            } else {
                showNotification(data.error || "Failed to import persona.", "error");
            }
        });
}

// ===================== INITIALIZE =====================

document.addEventListener("DOMContentLoaded", () => {
    LogPanel.bindUI();
    LogPanel.fetchLogs();
    ServiceStatus.fetchStatus();
    setInterval(LogPanel.fetchLogs, 5000);
    setInterval(ServiceStatus.fetchStatus, 10000);
    AudioPanel.updateDeviceLabels();
    PersonaForm.loadPersona();
    AudioPanel.loadMicGain();
    SettingsForm.handleSettingsSave();
    PersonaForm.handlePersonaSave();
    window.addBackstoryField = PersonaForm.addBackstoryField;
    MotorPanel.bindUI();
    Sections.collapsible();
});