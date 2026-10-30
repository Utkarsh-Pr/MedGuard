/* Renders conservative evidence returned by POST /scan. */
const STATUS_INFO = {
  ADVISORY_MATCH: { label: "ADVISORY MATCH", bannerClass: "safe", icon: "✅", badgeClass: "badge-safe" },
  WRONG_MEDICINE: { label: "WRONG MEDICINE", bannerClass: "danger", icon: "⚠️", badgeClass: "badge-danger" },
  WRONG_TIME: { label: "WRONG TIME", bannerClass: "warning", icon: "⏰", badgeClass: "badge-warning" },
  NOT_ON_LIST: { label: "NOT ON YOUR LIST", bannerClass: "danger", icon: "⚠️", badgeClass: "badge-danger" },
  EXPIRED: { label: "EXPIRED", bannerClass: "danger", icon: "⛔", badgeClass: "badge-danger" },
  RETAKE_REQUIRED: { label: "RETAKE PHOTO", bannerClass: "warning", icon: "📷", badgeClass: "badge-warning" },
  MANUAL_VERIFICATION: { label: "VERIFY MANUALLY", bannerClass: "warning", icon: "🔎", badgeClass: "badge-warning" },
};

document.addEventListener("DOMContentLoaded", function () {
  const patient = requirePatient();
  if (!patient) return;
  document.getElementById("logoutLink").addEventListener("click", function (e) { e.preventDefault(); logoutPatient(); });
  const result = loadData(STORAGE_KEYS.LAST_RESULT, null);
  const image = loadData(STORAGE_KEYS.LAST_SCAN_IMAGE, null);
  if (!result) { window.location.href = "scan.html"; return; }
  renderResult(result, image);
  document.getElementById("listenBtn").addEventListener("click", function () { speak(document.getElementById("page-announcement").textContent); });
});

function valueOrDash(value) { return value === null || value === undefined || value === "" ? "—" : value; }
function reasonLabel(reason) { return String(reason || "").replaceAll("_", " "); }

function renderResult(result, image) {
  const info = STATUS_INFO[result.status] || STATUS_INFO.MANUAL_VERIFICATION;
  const classifier = result.classifier || {};
  const ocr = result.ocr || {};
  const quality = result.imageQuality || {};
  document.getElementById("resultBanner").className = "result-banner " + info.bannerClass;
  document.getElementById("resultIcon").textContent = info.icon;
  const badge = document.getElementById("resultBadge"); badge.textContent = info.label; badge.className = "badge " + info.badgeClass;
  document.getElementById("resultMessage").textContent = result.message;
  if (image) document.getElementById("scannedImage").src = image;
  document.getElementById("detectedName").textContent = valueOrDash(result.detectedName);
  document.getElementById("detectedConfidence").textContent = valueOrDash(classifier.confidence ?? result.confidence) + "%";
  document.getElementById("detectedMargin").textContent = valueOrDash(classifier.margin) + "%";
  document.getElementById("classifierState").textContent = classifier.isUnknown ? "Unknown — do not guess" : "Recognized";
  document.getElementById("ocrName").textContent = valueOrDash(ocr.medicineName);
  document.getElementById("ocrDosage").textContent = valueOrDash(ocr.dosage);
  document.getElementById("ocrExpiry").textContent = valueOrDash(ocr.expiryDate);
  document.getElementById("ocrBatch").textContent = valueOrDash(ocr.batchNumber);
  document.getElementById("ocrConfidence").textContent = valueOrDash(ocr.confidence) + "%";
  document.getElementById("imageQuality").textContent = quality.retakeRequired ? "Retake required" : "Acceptable for analysis";
  document.getElementById("qualityReasons").textContent = (quality.reasons || []).map(reasonLabel).join(", ") || "No quality issues found.";
  document.getElementById("verificationReasons").textContent = (result.reasons || []).map(reasonLabel).join(", ") || "All required evidence agreed.";
  document.getElementById("ocrRawText").textContent = valueOrDash(ocr.rawText);
  const comparisonEl = document.getElementById("prescriptionComparison");
  if (result.matchedPrescription) {
    const p = result.matchedPrescription;
    comparisonEl.textContent = "Matches your prescription for " + p.name + " (" + p.dosage + "), scheduled: " + p.time.join(", ") + ", " + p.frequency + ".";
  } else { comparisonEl.textContent = result.status === "RETAKE_REQUIRED" ? "Could not compare — retake the photo first." : "No verified prescription match is available."; }
  document.getElementById("page-announcement").textContent = info.label + ". " + result.message + " Detected medicine: " + (result.detectedName || "not identified") + ".";
}
