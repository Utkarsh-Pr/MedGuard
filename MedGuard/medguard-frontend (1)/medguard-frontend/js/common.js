/* =========================================================
   MedGuard — common.js
   Small helper functions shared by every page:
     - the FastAPI backend's base URL + a fetch() helper
     - localStorage keys & read/write helpers
     - applying accessibility settings (font size / contrast)
     - text-to-speech helper (SpeechSynthesis)
     - a "logged in?" guard for pages that need a patient
   Loaded on every page BEFORE the page's own script.
   ========================================================= */

// ---- Backend API ----
// Change this if your FastAPI server runs somewhere else.
const API_BASE_URL = "http://localhost:8000";

// Small wrapper around fetch() for talking to the FastAPI backend.
// - Automatically sends/reads JSON.
// - Throws a readable Error if the request fails, so callers can
//   show a friendly message instead of a silent failure.
async function apiRequest(path, options) {
  const opts = options || {};
  const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});

  let response;
  try {
    response = await fetch(API_BASE_URL + path, Object.assign({}, opts, { headers }));
  } catch (err) {
    throw new Error("Could not reach the MedGuard server. Is the backend running?");
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || detail;
    } catch (_) {
      // response wasn't JSON — keep the default statusText
    }
    throw new Error(detail);
  }

  // Some endpoints (like DELETE) may return no content.
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

// ---- localStorage keys (kept in one place so they never get mistyped) ----
// PRESCRIPTIONS and HISTORY now live in PostgreSQL (via the FastAPI
// backend) instead of localStorage — see prescription.js / history.js.
const STORAGE_KEYS = {
  PATIENT: "medguard_patient",
  SETTINGS: "medguard_settings",
  LAST_SCAN_IMAGE: "medguard_last_scan_image",
  LAST_RESULT: "medguard_last_result",
};

// ---- Generic localStorage helpers ----
function loadData(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (err) {
    console.error("MedGuard: failed to read", key, err);
    return fallback;
  }
}

function saveData(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (err) {
    console.error("MedGuard: failed to save", key, err);
  }
}

// ---- Settings (accessibility) ----
const DEFAULT_SETTINGS = {
  fontScale: 1,       // multiplies the base font size
  highContrast: false,
  voiceEnabled: true,
};

function getSettings() {
  return Object.assign({}, DEFAULT_SETTINGS, loadData(STORAGE_KEYS.SETTINGS, {}));
}

function saveSettings(settings) {
  saveData(STORAGE_KEYS.SETTINGS, settings);
  applySettings(settings);
}

// Applies font scale + contrast to the whole page by setting
// attributes/CSS variables on the <html> element.
function applySettings(settings) {
  const s = settings || getSettings();
  document.documentElement.style.setProperty("--font-scale", s.fontScale);
  if (s.highContrast) {
    document.documentElement.setAttribute("data-contrast", "high");
  } else {
    document.documentElement.removeAttribute("data-contrast");
  }
}

// Run immediately on every page load, before the rest of the page renders.
applySettings(getSettings());

// ---- Text-to-speech helper ----
// Reads the given text aloud, if voice is enabled in settings and the
// browser supports SpeechSynthesis. Safe to call even if unsupported.
function speak(text) {
  const settings = getSettings();
  if (!settings.voiceEnabled) return;
  if (!("speechSynthesis" in window)) {
    console.warn("MedGuard: SpeechSynthesis not supported in this browser.");
    return;
  }
  window.speechSynthesis.cancel(); // stop anything already playing
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95; // slightly slower — easier to follow for elderly users
  window.speechSynthesis.speak(utterance);
}

// ---- Patient / login helpers ----
function getCurrentPatient() {
  return loadData(STORAGE_KEYS.PATIENT, null);
}

// Call this at the top of any page that requires a logged-in patient.
// Redirects back to the login page if nobody is selected yet.
function requirePatient() {
  const patient = getCurrentPatient();
  if (!patient) {
    window.location.href = "index.html";
  }
  return patient;
}

function logoutPatient() {
  localStorage.removeItem(STORAGE_KEYS.PATIENT);
  window.location.href = "index.html";
}

// ---- Floating accessibility button ----
// Adds a small floating "read page" button (🔊) to pages that include
// an element with id="page-announcement". Pressing it reads that text
// aloud. This gives every page a quick voice affordance without
// duplicating markup.
function setupAccessibilityFab() {
  const announcement = document.getElementById("page-announcement");
  const fab = document.getElementById("accessibilityFab");
  if (!fab) return;
  fab.addEventListener("click", function () {
    const text = announcement ? announcement.textContent : document.title;
    speak(text);
  });
}

document.addEventListener("DOMContentLoaded", setupAccessibilityFab);
