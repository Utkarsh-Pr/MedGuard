/* =========================================================
   MedGuard — settings.js
   Lets the user adjust font size, high contrast, and voice —
   saved to localStorage and applied instantly (see common.js
   applySettings()).
   ========================================================= */

const FONT_SCALE_MIN = 0.85;
const FONT_SCALE_MAX = 1.6;
const FONT_SCALE_STEP = 0.15;

document.addEventListener("DOMContentLoaded", function () {
  const patient = requirePatient();
  if (!patient) return;

  document.getElementById("logoutLink").addEventListener("click", function (e) {
    e.preventDefault();
    logoutPatient();
  });

  const settings = getSettings();
  updateFontLabel(settings.fontScale);
  document.getElementById("contrastToggle").checked = settings.highContrast;
  document.getElementById("voiceToggle").checked = settings.voiceEnabled;

  document.getElementById("increaseFontBtn").addEventListener("click", function () {
    changeFontScale(FONT_SCALE_STEP);
  });
  document.getElementById("decreaseFontBtn").addEventListener("click", function () {
    changeFontScale(-FONT_SCALE_STEP);
  });

  document.getElementById("contrastToggle").addEventListener("change", function (e) {
    const s = getSettings();
    s.highContrast = e.target.checked;
    saveSettings(s);
  });

  document.getElementById("voiceToggle").addEventListener("change", function (e) {
    const s = getSettings();
    s.voiceEnabled = e.target.checked;
    saveSettings(s);
  });

  document.getElementById("testVoiceBtn").addEventListener("click", function () {
    speak("This is how MedGuard will sound when reading results aloud.");
  });
});

function changeFontScale(delta) {
  const s = getSettings();
  let newScale = Math.round((s.fontScale + delta) * 100) / 100;
  newScale = Math.max(FONT_SCALE_MIN, Math.min(FONT_SCALE_MAX, newScale));
  s.fontScale = newScale;
  saveSettings(s);
  updateFontLabel(newScale);
}

function updateFontLabel(scale) {
  document.getElementById("fontScaleLabel").textContent =
    Math.round(scale * 100) + "%";
}
