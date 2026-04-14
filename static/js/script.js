const form = document.querySelector(".form-col");
const loading = document.getElementById("loading");
const timerEl = document.querySelector(".loading-timer");
const startIpInput = document.querySelector("input[name='start_ip']");
const endIpInput = document.querySelector("input[name='end_ip']");
const maskInput = document.querySelector("input[name='mask']");
const presetButtons = document.querySelectorAll(".preset-btn");
const presetModal = document.getElementById("presetModal");
const openPresetModalBtn = document.getElementById("openPresetModal");
const closePresetModalBtn = document.getElementById("closePresetModal");
const presetLabelInput = document.getElementById("presetLabelInput");
const presetFeedback = document.querySelector(".preset-feedback");
const inlineError = document.querySelector(".inline-error");
let timerId = null;

if (form) {
    form.addEventListener("submit", () => {
    loading.classList.add("show");
    const start = Date.now();
    timerEl.textContent = "00:00";
    if (timerId) clearInterval(timerId);
    timerId = setInterval(() => {
        const elapsed = Math.floor((Date.now() - start) / 1000);
        const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
        const ss = String(elapsed % 60).padStart(2, "0");
        timerEl.textContent = `${mm}:${ss}`;
    }, 500);
    });
}

function openPresetModal() {
    presetModal.classList.add("show");
    window.setTimeout(() => presetLabelInput?.focus(), 30);
}

function closePresetModal() {
    presetModal.classList.remove("show");
}

openPresetModalBtn?.addEventListener("click", openPresetModal);
closePresetModalBtn?.addEventListener("click", closePresetModal);
presetModal?.addEventListener("click", (event) => {
    if (event.target === presetModal) {
    closePresetModal();
    }
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && presetModal?.classList.contains("show")) {
    closePresetModal();
    }
});

if (presetFeedback) {
    setTimeout(() => {
    presetFeedback.classList.add("is-hidden");
    }, 3200);
}

if (inlineError) {
    setTimeout(() => {
    inlineError.classList.add("is-hidden");
    }, 3200);
}

function ipToInt(ip) {
    const parts = ip.split(".").map(Number);
    if (parts.length !== 4 || parts.some((p) => Number.isNaN(p) || p < 0 || p > 255)) {
    return null;
    }
    return ((parts[0] << 24) >>> 0) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
}

function intToMask(prefix) {
    if (prefix < 0 || prefix > 32) return "";
    const mask = prefix === 0 ? 0 : (~0 << (32 - prefix)) >>> 0;
    return [
    (mask >>> 24) & 255,
    (mask >>> 16) & 255,
    (mask >>> 8) & 255,
    mask & 255
    ].join(".");
}

function commonPrefixLen(a, b) {
    let x = (a ^ b) >>> 0;
    if (x === 0) return 32;
    let n = 0;
    while ((x & 0x80000000) === 0) {
    n++;
    x = (x << 1) >>> 0;
    }
    return n;
}

function updateMask() {
    const start = startIpInput.value.trim();
    const end = endIpInput.value.trim();
    const a = ipToInt(start);
    const b = ipToInt(end);
    if (a === null || b === null) {
    maskInput.value = "";
    return;
    }
    const prefix = commonPrefixLen(a, b);
    maskInput.value = intToMask(prefix);
}

function syncActivePreset() {
    const start = startIpInput.value.trim();
    const end = endIpInput.value.trim();

    presetButtons.forEach((button) => {
    const isActive = button.dataset.startIp === start && button.dataset.endIp === end;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
}

presetButtons.forEach((button) => {
    button.addEventListener("click", () => {
    startIpInput.value = button.dataset.startIp;
    endIpInput.value = button.dataset.endIp;
    updateMask();
    syncActivePreset();
    });
});

startIpInput.addEventListener("input", () => {
    updateMask();
    syncActivePreset();
});
endIpInput.addEventListener("input", () => {
    updateMask();
    syncActivePreset();
});

updateMask();
syncActivePreset();