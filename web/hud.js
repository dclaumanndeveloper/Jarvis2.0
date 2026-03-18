// --- HUD DATA MANAGEMENT ---
const metrics = {
    left: [
        { id: 'cpu', label: 'CPU LOAD', value: 0 },
        { id: 'ram', label: 'MEM ALLOC', value: 0 },
        { id: 'net', label: 'NET PKT', value: 0 },
        { id: 'hdd', label: 'DISK I/O', value: 0 },
    ],
    right: [
        { id: 'ai', label: 'NEURAL LINK', value: 0 },
        { id: 'pwr', label: 'CORE TEMP', value: 0 },
        { id: 'thr', label: 'THREAT LVL', value: 0 },
        { id: 'sync', label: 'SYNC RATE', value: 0 },
    ]
};

function initMetrics() {
    const renderMetric = (m) => `
        <div class="metric-row" id="metric-${m.id}">
            <div class="metric-label">${m.label}</div>
            <div class="metric-value-wrap">
                <div class="metric-value" id="val-${m.id}">${m.value}%</div>
            </div>
            <div class="metric-bar-bg">
                <div class="metric-bar-fill" id="bar-${m.id}" style="width: ${m.value}%"></div>
            </div>
        </div>
    `;

    document.getElementById('left-metrics').innerHTML = metrics.left.map(renderMetric).join('');
    document.getElementById('right-metrics').innerHTML = metrics.right.map(renderMetric).join('');
}

function updateMetric(id, value) {
    const valEl = document.getElementById(`val-${id}`);
    const barEl = document.getElementById(`bar-${id}`);
    if (valEl && barEl) {
        valEl.innerText = `${value.toFixed(1)}%`;
        barEl.style.width = `${value}%`;
    }
}

// --- ANIMATION HELPERS (vanilla JS, no GSAP) ---
function fadeOut(el, duration, onComplete) {
    el.style.transition = `opacity ${duration}ms`;
    el.style.opacity = '0';
    setTimeout(onComplete || (() => {}), duration);
}

function fadeIn(el, duration) {
    el.style.transition = `opacity ${duration}ms`;
    el.style.opacity = '1';
}

function slideIn(el, fromX, duration) {
    el.style.transition = `transform ${duration}ms, opacity ${duration}ms`;
    el.style.transform = `translateX(${fromX}px)`;
    el.style.opacity = '0';
    setTimeout(() => {
        el.style.transform = 'translateX(0)';
        el.style.opacity = '1';
    }, 10);
}

function slideDown(el, fromY, duration) {
    el.style.transition = `transform ${duration}ms, opacity ${duration}ms`;
    el.style.transform = `translateY(${fromY}px)`;
    el.style.opacity = '0';
    setTimeout(() => {
        el.style.transform = 'translateY(0)';
        el.style.opacity = '1';
    }, 10);
}

// --- PYTHON BRIDGE (QWebChannel) ---
function initBridge() {
    if (typeof QWebChannel !== 'undefined') {
        new QWebChannel(qt.webChannelTransport, function (channel) {
            window.jarvis_bridge = channel.objects.jarvis_bridge;
            console.log("HUD: QWebChannel Bridge Connected!");

            // Map signals to existing UI logic
            window.jarvis_bridge.metrics_updated.connect((json_data) => {
                const data = JSON.parse(json_data);
                window.jarvis_hud.update_metrics(data);
            });

            window.jarvis_bridge.waveform_updated.connect((level) => {
                window.jarvis_hud.update_waveform(level);
            });

            window.jarvis_bridge.state_changed.connect((state) => {
                window.jarvis_hud.set_state(state);
            });

            window.jarvis_bridge.message_shown.connect((msg) => {
                window.jarvis_hud.show_message(msg);
            });

            window.jarvis_bridge.token_streamed.connect((token) => {
                window.jarvis_hud.append_token(token);
            });

            // Initial reveal animation using vanilla JS (faster)
            document.querySelectorAll('.panel').forEach((panel, i) => {
                slideIn(panel, i === 0 ? -100 : 100, 600);
            });
            slideDown(document.getElementById('hud-header'), -50, 600);
        });
    } else {
        console.warn("HUD: QWebChannel not found, falling back to legacy mode.");
    }
}

// APIs called by Python
window.jarvis_hud = {
    update_response: (text) => {
        const el = document.getElementById('response-text');
        fadeOut(el, 200, () => {
            el.innerText = text;
            fadeIn(el, 500);
        });
    },
    update_metrics: (data) => {
        // data looks like { cpu: 20, ram: 45, etc }
        for (const [key, val] of Object.entries(data)) {
            updateMetric(key, val);
        }
    },
    set_status: (text, show = true) => {
        const el = document.getElementById('status-overlay');
        const txt = document.getElementById('status-text');
        txt.innerText = text;
        el.style.display = show ? 'flex' : 'none';
        if (show) {
            el.style.transform = 'scale(1.5)';
            el.style.opacity = '0';
            setTimeout(() => {
                el.style.transition = 'transform 500ms, opacity 500ms';
                el.style.transform = 'scale(1)';
                el.style.opacity = '1';
            }, 10);
        }
    },
    set_state: (state) => {
        const reactorEl = document.getElementById('reactor-canvas-container');
        const statusEl = document.getElementById('status-overlay');
        const statusText = document.getElementById('status-text');

        // Clear old state classes
        reactorEl.classList.remove('pulse-active', 'speaking-active');

        if (state === 'LISTENING') {
            reactorEl.classList.add('pulse-active');
            statusText.innerText = 'LISTENING...';
            statusEl.style.display = 'flex';
            statusEl.style.transition = 'opacity 300ms';
            statusEl.style.opacity = '1';
            statusEl.style.pointerEvents = 'auto';

            // Stop speaking waveform animation if any
            if (window._speakingInterval) {
                clearInterval(window._speakingInterval);
                window._speakingInterval = null;
            }
        } else if (state === 'SPEAKING') {
            // Arc reactor glows brighter when speaking
            reactorEl.classList.add('speaking-active');
            statusText.innerText = 'RESPONDING...';
            statusEl.style.display = 'flex';
            statusEl.style.transition = 'opacity 200ms';
            statusEl.style.opacity = '1';
            statusEl.style.pointerEvents = 'auto';

            // Animate waveform as if audio is coming out (simulate pulse)
            window._speakingInterval = setInterval(() => {
                audioLevel = 0.4 + Math.random() * 0.5;
            }, 80);

        } else {
            // IDLE / PROCESSING / etc. - HIDE overlay completely
            if (window._speakingInterval) {
                clearInterval(window._speakingInterval);
                window._speakingInterval = null;
            }
            statusEl.style.transition = 'opacity 300ms';
            statusEl.style.opacity = '0';
            statusEl.style.pointerEvents = 'none';
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 300);
        }
    },
    show_message: (msg) => {
        const el = document.getElementById('response-text');
        // If it starts with JARVIS:, we might want to preserve it or just clear for streaming
        if (msg.startsWith('JARVIS: ')) {
            window._currentResponseText = "";
            // Reset token streaming state for the new request
            window._tokenBuffer = "";
            window._isStreamingResponse = false;
        }
        fadeOut(el, 200, () => {
            el.innerText = msg;
            fadeIn(el, 400);
        });
    },
    append_token: (token) => {
        const el = document.getElementById('response-text');
        
        // Initialize if first token
        if (!window._tokenBuffer) {
            window._tokenBuffer = "";
            window._isStreamingResponse = false;
        }
        
        window._tokenBuffer += token;
        
        // Look for the start of the suggested_response content: "suggested_response": "
        const trigger = '"suggested_response": "';
        if (!window._isStreamingResponse) {
            const index = window._tokenBuffer.indexOf(trigger);
            if (index !== -1) {
                window._isStreamingResponse = true;
                window._currentResponseText = "JARVIS: ";
                // Everything after the trigger
                window._currentResponseText += window._tokenBuffer.substring(index + trigger.length);
            }
        } else {
            // We are already streaming the core response
            // Stop if we hit the end quote (simple check)
            if (token === '"' && !window._tokenBuffer.endsWith('\\"')) {
                window._isStreamingResponse = false;
            } else {
                window._currentResponseText += token;
            }
        }

        if (window._isStreamingResponse) {
            el.innerText = window._currentResponseText;
            el.style.opacity = 1;
        }
    },
    update_waveform: (level) => {
        // Boost level for visibility
        audioLevel = Math.max(audioLevel, level);
    }
};

// --- VOICE WAVEFORM ---
let waveCanvas, waveCtx;
let audioLevel = 0;

function initWaveform() {
    waveCanvas = document.getElementById('voice-visualizer');
    waveCtx = waveCanvas.getContext('2d');
    resizeWaveform();
    window.addEventListener('resize', resizeWaveform);
    drawWave();
}

function resizeWaveform() {
    waveCanvas.width = waveCanvas.parentElement.clientWidth;
    waveCanvas.height = waveCanvas.parentElement.clientHeight;
}

function drawWave() {
    requestAnimationFrame(drawWave);
    if (!waveCtx) return;

    waveCtx.clearRect(0, 0, waveCanvas.width, waveCanvas.height);

    const centerY = waveCanvas.height / 2;
    const width = waveCanvas.width;
    const time = Date.now() * 0.005;

    // Drawing multiple layers of waves
    for (let j = 0; j < 3; j++) {
        waveCtx.beginPath();
        waveCtx.lineWidth = j === 0 ? 3 : 1;
        waveCtx.strokeStyle = j === 0 ? 'rgba(0, 255, 255, 1)' : 'rgba(0, 255, 255, 0.3)';

        const float_height = 10 + (audioLevel * 100 * (j + 1) * 0.5);

        for (let i = 0; i < width; i++) {
            const x = i;
            const y = centerY + Math.sin(x * 0.05 + time + j) * float_height * Math.sin(x * 0.01 + time * 0.5);
            if (i === 0) waveCtx.moveTo(x, y);
            else waveCtx.lineTo(x, y);
        }
        waveCtx.stroke();
    }

    // Decay audio level
    audioLevel *= 0.9;
}

// Waveform logic handled above

// --- CLOCK UPDATE ---
function updateClock() {
    const el = document.getElementById('current-time');
    if (el) {
        const now = new Date();
        el.innerText = now.toLocaleTimeString('pt-BR', { hour12: false });
    } else {
        console.warn('Clock element not found');
    }
}

// --- INITIALIZATION ---
// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeHUD);
} else {
    initializeHUD();
}

function initializeHUD() {
    console.log('Initializing HUD...');

    // Start visual components first
    initMetrics();
    initWaveform();

    // Start clock immediately
    updateClock();
    setInterval(updateClock, 1000);

    // Hide status overlay on init
    const statusOverlay = document.getElementById('status-overlay');
    if (statusOverlay) {
        statusOverlay.style.display = 'none';
        statusOverlay.style.opacity = '0';
        statusOverlay.style.pointerEvents = 'none';
    }

    // Initialize bridge last (waits for QWebChannel)
    initBridge();

    console.log('HUD initialized');
}
