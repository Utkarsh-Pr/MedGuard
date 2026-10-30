/* =========================================================
   MedGuard — scan.js

   Handles:
     1) Choosing an image (file upload OR live camera capture)
     2) Sending it to the FastAPI backend's POST /scan endpoint
        and showing the returned safety-check result

   The backend runs quality checks, calibrated ONNX classification,
   OCR, expiry parsing, and conservative prescription comparison.
   A weak or incomplete image is shown as a retake/manual-verification
   result rather than a guessed medicine.
   ========================================================= */

let selectedImageDataUrl = null; // used for on-page + result-page preview
let selectedImageBlob = null;    // the actual file/blob sent to the backend
let cameraStream = null;

document.addEventListener("DOMContentLoaded", function () {
  const patient = requirePatient();
  if (!patient) return;

  document.getElementById("logoutLink") &&
    document.getElementById("logoutLink").addEventListener("click", function (e) {
      e.preventDefault();
      logoutPatient();
    });

  document.getElementById("fileInput").addEventListener("change", handleFileSelect);
  document.getElementById("cameraBtn").addEventListener("click", openCamera);
  document.getElementById("closeCameraBtn").addEventListener("click", closeCamera);
  document.getElementById("captureBtn").addEventListener("click", capturePhoto);
  document.getElementById("scanBtn").addEventListener("click", runScan);
});

// ---------- Choosing an image ----------

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  selectedImageBlob = file;

  const reader = new FileReader();
  reader.onload = function (e) {
    setPreviewImage(e.target.result);
  };
  reader.readAsDataURL(file);
}

function setPreviewImage(dataUrl) {
  selectedImageDataUrl = dataUrl;
  document.getElementById("previewImage").src = dataUrl;
  document.getElementById("previewWrap").hidden = false;
  document.getElementById("scanDrop").hidden = true;
  document.getElementById("scanBtn").disabled = false;
}

// ---------- Camera capture (basic getUserMedia + canvas) ----------

function openCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Camera is not supported in this browser. Please upload a photo instead.");
    return;
  }

  navigator.mediaDevices
    .getUserMedia({ video: { facingMode: "environment" } })
    .then(function (stream) {
      cameraStream = stream;
      const video = document.getElementById("cameraVideo");
      video.srcObject = stream;
      document.getElementById("cameraWrap").hidden = false;
    })
    .catch(function (err) {
      console.error("MedGuard: camera error", err);
      alert("Could not access camera. Please check permissions or upload a photo instead.");
    });
}

function capturePhoto() {
  const video = document.getElementById("cameraVideo");
  const canvas = document.getElementById("captureCanvas");

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

  // Keep a data URL for the on-screen preview...
  const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
  setPreviewImage(dataUrl);

  // ...and a real Blob (like a file) to upload to the backend.
  canvas.toBlob(
    function (blob) {
      selectedImageBlob = blob;
    },
    "image/jpeg",
    0.9
  );

  closeCamera();
}

function closeCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  document.getElementById("cameraWrap").hidden = true;
}

// ---------- Sending the image to the backend ----------

async function runScan() {
  if (!selectedImageBlob) return;

  const patient = getCurrentPatient();
  const scanBtn = document.getElementById("scanBtn");

  scanBtn.disabled = true;
  document.getElementById("scanningState").hidden = false;

  try {
    const formData = new FormData();
    formData.append("patient_id", patient.id);
    formData.append("image", selectedImageBlob, "scan.jpg");

    // NOTE: apiRequest() (common.js) always sets a JSON Content-Type
    // header, which breaks file uploads — so this one call uses
    // fetch() directly and lets the browser set the correct
    // multipart/form-data header (with boundary) itself.
    const response = await fetch(API_BASE_URL + "/scan", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || "The scan could not be completed.");
    }

    const result = await response.json();

    saveData(STORAGE_KEYS.LAST_SCAN_IMAGE, selectedImageDataUrl);
    saveData(STORAGE_KEYS.LAST_RESULT, result);

    window.location.href = "result.html";
  } catch (err) {
    alert(err.message);
    scanBtn.disabled = false;
    document.getElementById("scanningState").hidden = true;
  }
}
