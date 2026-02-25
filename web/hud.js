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

// --- THREE.JS ARC REACTOR ---
let scene, camera, renderer, reactor;

function initThree() {
    const container = document.getElementById('reactor-canvas-container');
    const width = container.clientWidth;
    const height = container.clientHeight;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    // Create HUD Rings (Torus/Ring Geometries)
    const ringGroup = new THREE.Group();

    // Outer Ring
    const outerGeometry = new THREE.TorusGeometry(2, 0.05, 16, 100);
    const outerMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff, transparent: true, opacity: 0.5 });
    const outerRing = new THREE.Mesh(outerGeometry, outerMaterial);
    ringGroup.add(outerRing);

    // Inner Segmented Ring
    const innerGeometry = new THREE.RingGeometry(1.5, 1.7, 32);
    const innerMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff, side: THREE.DoubleSide, transparent: true, opacity: 0.3 });
    const innerRing = new THREE.Mesh(innerGeometry, innerMaterial);
    ringGroup.add(innerRing);

    // Center Core (Sphere with high emissive look)
    const coreGeometry = new THREE.SphereGeometry(0.5, 32, 32);
    const coreMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    ringGroup.add(core);

    // Add some glow lines
    for (let i = 0; i < 12; i++) {
        const lineGeom = new THREE.BoxGeometry(0.1, 0.8, 0.1);
        const lineMat = new THREE.MeshBasicMaterial({ color: 0x00ffff });
        const line = new THREE.Mesh(lineGeom, lineMat);
        line.position.y = 1.0;
        const pivot = new THREE.Group();
        pivot.add(line);
        pivot.rotation.z = (i / 12) * Math.PI * 2;
        ringGroup.add(pivot);
    }

    scene.add(ringGroup);
    reactor = ringGroup;

    animate();
}

function animate() {
    requestAnimationFrame(animate);
    if (reactor) {
        reactor.rotation.z += 0.005;
        reactor.children[0].rotation.y += 0.01; // Outer ring spin
    }
    renderer.render(scene, camera);
}

// --- PYTHON BRIDGE ---
window.addEventListener('pywebviewready', function () {
    console.log("HUD Bridge Ready");
    // Initial reveal animation
    gsap.from(".panel", { duration: 1, opacity: 0, x: (i) => i === 0 ? -100 : 100, stagger: 0.5 });
    gsap.from("#hud-header", { duration: 1, y: -50, opacity: 0 });
});

// APIs called by Python
window.jarvis_hud = {
    update_response: (text) => {
        const el = document.getElementById('response-text');
        gsap.to(el, {
            duration: 0.2, opacity: 0, onComplete: () => {
                el.innerText = text;
                gsap.to(el, { duration: 0.5, opacity: 1 });
            }
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
        if (show) gsap.from(el, { scale: 1.5, opacity: 0, duration: 0.5 });
    },
    set_state: (state) => {
        const reactorEl = document.getElementById('reactor-canvas-container');
        const statusEl = document.getElementById('status-overlay');
        const statusText = document.getElementById('status-text');

        if (state === 'LISTENING') {
            reactorEl.classList.add('pulse-active');
            statusText.innerText = 'LISTENING...';
            statusEl.style.display = 'flex';
            gsap.to(statusEl, { opacity: 1, duration: 0.3 });
        } else {
            reactorEl.classList.remove('pulse-active');
            gsap.to(statusEl, {
                opacity: 0, duration: 0.5, onComplete: () => {
                    statusEl.style.display = 'none';
                }
            });
        }
    },
    show_message: (msg) => {
        const el = document.getElementById('response-text');
        // Simple typewriter or fade effect
        gsap.to(el, {
            opacity: 0, duration: 0.2, onComplete: () => {
                el.innerText = msg;
                gsap.to(el, { opacity: 1, x: 0, duration: 0.4 });
            }
        });
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

// Start everything
initMetrics();
initThree();
initWaveform();
