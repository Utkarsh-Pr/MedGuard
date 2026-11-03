/* =========================================================
   MedGuard — prescription.js
   Add / edit / delete prescriptions. Data now lives in
   PostgreSQL via the FastAPI backend (see common.js for
   API_BASE_URL / apiRequest()) instead of localStorage.

   The backend uses slightly different field names than this
   page's form (e.g. "medicine_name" instead of "name",
   "start_date" instead of "startDate") — toApiPayload() and
   fromApiPrescription() below convert between the two so the
   rest of this file (and the HTML) didn't need to change.
   ========================================================= */

let currentPrescriptions = []; // cached list for the logged-in patient
let ocrDraft = null;

document.addEventListener("DOMContentLoaded", function () {
  const patient = requirePatient();
  if (!patient) return;

  const form = document.getElementById("prescriptionForm");
  const cancelEditBtn = document.getElementById("cancelEditBtn");

  document.getElementById("logoutLink").addEventListener("click", function (e) {
    e.preventDefault();
    logoutPatient();
  });

  form.addEventListener("submit", handleSubmit);
  cancelEditBtn.addEventListener("click", resetForm);
  document.getElementById("prescriptionImageInput").addEventListener("change", previewPrescriptionImage);
  document.getElementById("scanPrescriptionBtn").addEventListener("click", scanPrintedPrescription);
  document.getElementById("ocrReviewForm").addEventListener("submit", saveReviewedCandidates);

  renderList();
});

function getTimeCheckboxes() {
  return {
    morning: document.getElementById("timeMorning"),
    afternoon: document.getElementById("timeAfternoon"),
    evening: document.getElementById("timeEvening"),
    night: document.getElementById("timeNight"),
  };
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function previewPrescriptionImage() {
  const input = document.getElementById("prescriptionImageInput");
  const file = input.files[0];
  const preview = document.getElementById("prescriptionPreview");
  const wrap = document.getElementById("prescriptionPreviewWrap");
  document.getElementById("scanPrescriptionBtn").disabled = !file;
  document.getElementById("ocrReviewSection").hidden = true;
  if (!file) { wrap.hidden = true; preview.removeAttribute("src"); return; }
  preview.src = URL.createObjectURL(file);
  wrap.hidden = false;
}

async function scanPrintedPrescription() {
  const patient = getCurrentPatient();
  const file = document.getElementById("prescriptionImageInput").files[0];
  const status = document.getElementById("prescriptionOcrState");
  const button = document.getElementById("scanPrescriptionBtn");
  if (!file || !patient) return;
  if (file.size > 10 * 1024 * 1024) { status.textContent = "Choose an image under 10 MB."; return; }
  button.disabled = true;
  status.textContent = "Reading printed prescription…";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  const data = new FormData();
  data.append("patient_id", patient.id);
  data.append("image", file);
  try {
    const response = await fetch(API_BASE_URL + "/prescriptions/ocr", { method: "POST", body: data, signal: controller.signal });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body.detail;
      const message = typeof detail === "object" ? (detail.message || (detail.reasons || []).join(", ")) : detail;
      throw new Error(message || "Could not read this prescription photo.");
    }
    ocrDraft = body;
    renderOcrDraft(body);
    status.textContent = "Draft ready. Review every field before saving.";
  } catch (error) {
    status.textContent = error.name === "AbortError" ? "The scan took over 30 seconds. Check the backend and try a clearer photo." : error.message;
  } finally {
    clearTimeout(timeout);
    button.disabled = false;
  }
}

function renderOcrDraft(draft) {
  const section = document.getElementById("ocrReviewSection");
  const list = document.getElementById("ocrCandidateList");
  const warnings = document.getElementById("ocrWarnings");
  document.getElementById("ocrRawText").textContent = draft.rawText || "No text returned.";
  warnings.textContent = (draft.warnings || []).join(" ");
  warnings.hidden = !draft.warnings || draft.warnings.length === 0;
  list.innerHTML = "";
  draft.candidates.forEach((candidate, index) => {
    const times = candidate.time || [];
    const card = document.createElement("article");
    card.className = "ocr-candidate";
    card.dataset.index = index;
    card.innerHTML = `
      <div class="row"><h3 style="flex:1">Candidate ${index + 1}</h3><button type="button" class="btn btn-secondary remove-ocr-candidate">Remove</button></div>
      <p class="text-muted">OCR confidence: ${Math.round((candidate.confidence || 0) * 100)}% · Source: ${escapeHtml(candidate.rawLine)}</p>
      <div class="form-group"><label>Medicine name <input class="ocr-name" required value="${escapeHtml(candidate.medicineName)}" /></label></div>
      <div class="row">
        <div class="form-group" style="flex:1"><label>Strength / dosage <input class="ocr-dosage" required value="${escapeHtml(candidate.dosage)}" /></label></div>
        <div class="form-group" style="flex:1"><label>Tablets per dose <input class="ocr-tablets" type="number" min="1" step="1" required value="${candidate.tablets || ""}" /></label></div>
      </div>
      <fieldset><legend>Time of day (required)</legend>${["morning", "afternoon", "evening", "night"].map((time) => `<span class="checkbox-row"><input class="ocr-time" type="checkbox" value="${time}" ${times.includes(time) ? "checked" : ""}/><label style="margin:0">${time[0].toUpperCase() + time.slice(1)}</label></span>`).join("")}</fieldset>
      <div class="form-group"><label>Frequency <select class="ocr-frequency" required>${["", "Once daily", "Twice daily", "Thrice daily", "As needed"].map((value) => `<option value="${value}" ${candidate.frequency === value ? "selected" : ""}>${value || "Select frequency"}</option>`).join("")}</select></label></div>
      <div class="row"><div class="form-group" style="flex:1"><label>Start date <input class="ocr-start" type="date" required value="${escapeHtml(candidate.startDate)}" /></label></div><div class="form-group" style="flex:1"><label>End date <input class="ocr-end" type="date" required value="${escapeHtml(candidate.endDate)}" /></label></div></div>
      ${candidate.courseDays ? `<p class="text-muted">OCR read a course of ${candidate.courseDays} days. Confirm the dates with the prescription.</p>` : ""}
      ${candidate.instructions ? `<p class="text-muted">OCR note: ${escapeHtml(candidate.instructions)}</p>` : ""}
      ${(candidate.warnings || []).length ? `<p class="ocr-candidate-warning">${escapeHtml(candidate.warnings.join(" "))}</p>` : ""}`;
    card.querySelector(".remove-ocr-candidate").addEventListener("click", () => card.remove());
    list.appendChild(card);
  });
  section.hidden = false;
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function saveReviewedCandidates(event) {
  event.preventDefault();
  const cards = Array.from(document.querySelectorAll(".ocr-candidate"));
  if (!cards.length) { alert("Keep at least one candidate or use the manual form below."); return; }
  const patient = getCurrentPatient();
  const prepared = [];
  for (const card of cards) {
    const times = Array.from(card.querySelectorAll(".ocr-time:checked")).map((input) => input.value);
    if (!times.length) { alert("Choose at least one time of day for every reviewed medicine."); return; }
    const prescription = {
      name: card.querySelector(".ocr-name").value.trim(), dosage: card.querySelector(".ocr-dosage").value.trim(),
      tablets: Number(card.querySelector(".ocr-tablets").value), time: times,
      frequency: card.querySelector(".ocr-frequency").value, startDate: card.querySelector(".ocr-start").value,
      endDate: card.querySelector(".ocr-end").value,
    };
    if (!prescription.name || !prescription.dosage || !prescription.tablets || !prescription.frequency || !prescription.startDate || !prescription.endDate) {
      alert("Complete every reviewed field before saving."); return;
    }
    prepared.push(prescription);
  }
  const button = document.getElementById("saveOcrCandidatesBtn");
  button.disabled = true;
  try {
    for (const prescription of prepared) await apiRequest("/prescriptions", { method: "POST", body: JSON.stringify(toApiPayload(prescription, patient.id)) });
    document.getElementById("ocrReviewSection").hidden = true;
    document.getElementById("prescriptionOcrState").textContent = "Reviewed medicines saved.";
    await renderList();
  } catch (error) {
    alert("Could not save reviewed medicine: " + error.message);
  } finally {
    button.disabled = false;
  }
}

// ---- Field-name mapping between this page and the FastAPI backend ----

function toApiPayload(prescription, patientId) {
  return {
    patient_id: patientId,
    medicine_name: prescription.name,
    strength: prescription.dosage,
    tablets: prescription.tablets,
    time: prescription.time,
    frequency: prescription.frequency,
    start_date: prescription.startDate,
    end_date: prescription.endDate,
  };
}

function fromApiPrescription(apiRx) {
  return {
    id: apiRx.id,
    name: apiRx.medicine_name,
    dosage: apiRx.strength,
    tablets: apiRx.tablets,
    time: apiRx.time,
    frequency: apiRx.frequency,
    startDate: apiRx.start_date,
    endDate: apiRx.end_date,
  };
}

async function handleSubmit(event) {
  event.preventDefault();

  const patient = getCurrentPatient();
  const id = document.getElementById("prescriptionId").value;
  const checkboxes = getTimeCheckboxes();
  const selectedTimes = Object.keys(checkboxes).filter(
    (key) => checkboxes[key].checked
  );

  const prescription = {
    name: document.getElementById("medName").value.trim(),
    dosage: document.getElementById("medDosage").value.trim(),
    tablets: Number(document.getElementById("medTablets").value),
    time: selectedTimes,
    frequency: document.getElementById("medFrequency").value,
    startDate: document.getElementById("medStart").value,
    endDate: document.getElementById("medEnd").value,
  };

  const saveBtn = document.getElementById("saveBtn");
  saveBtn.disabled = true;

  try {
    if (id) {
      // Editing an existing prescription
      await apiRequest("/prescriptions/" + id, {
        method: "PUT",
        body: JSON.stringify(toApiPayload(prescription, patient.id)),
      });
    } else {
      // Adding a new prescription
      await apiRequest("/prescriptions", {
        method: "POST",
        body: JSON.stringify(toApiPayload(prescription, patient.id)),
      });
    }
    resetForm();
    await renderList();
  } catch (err) {
    alert("Could not save prescription: " + err.message);
  } finally {
    saveBtn.disabled = false;
  }
}

function resetForm() {
  const form = document.getElementById("prescriptionForm");
  form.reset();
  document.getElementById("prescriptionId").value = "";
  document.getElementById("formModeLabel").textContent = "Add a Medicine";
  document.getElementById("saveBtn").textContent = "Save Prescription";
  document.getElementById("cancelEditBtn").hidden = true;
}

function startEdit(prescription) {
  document.getElementById("prescriptionId").value = prescription.id;
  document.getElementById("medName").value = prescription.name;
  document.getElementById("medDosage").value = prescription.dosage;
  document.getElementById("medTablets").value = prescription.tablets;
  document.getElementById("medFrequency").value = prescription.frequency;
  document.getElementById("medStart").value = prescription.startDate;
  document.getElementById("medEnd").value = prescription.endDate;

  const checkboxes = getTimeCheckboxes();
  Object.keys(checkboxes).forEach((key) => {
    checkboxes[key].checked = prescription.time.includes(key);
  });

  document.getElementById("formModeLabel").textContent = "Edit Medicine";
  document.getElementById("saveBtn").textContent = "Update Prescription";
  document.getElementById("cancelEditBtn").hidden = false;

  // Scroll the form into view so the user sees what they're editing
  document.getElementById("prescriptionForm").scrollIntoView({ behavior: "smooth" });
}

async function deletePrescription(id) {
  const confirmed = window.confirm("Delete this prescription?");
  if (!confirmed) return;

  try {
    await apiRequest("/prescriptions/" + id, { method: "DELETE" });
    await renderList();
  } catch (err) {
    alert("Could not delete prescription: " + err.message);
  }
}

function timesLabel(times) {
  if (!times || times.length === 0) return "No time set";
  const order = ["morning", "afternoon", "evening", "night"];
  return order
    .filter((t) => times.includes(t))
    .map((t) => t.charAt(0).toUpperCase() + t.slice(1))
    .join(", ");
}

async function renderList() {
  const patient = getCurrentPatient();
  const list = document.getElementById("prescriptionList");
  const empty = document.getElementById("listEmpty");

  try {
    const apiPrescriptions = await apiRequest("/prescriptions/" + patient.id, {
      method: "GET",
    });
    currentPrescriptions = apiPrescriptions.map(fromApiPrescription);
  } catch (err) {
    list.innerHTML = "";
    empty.hidden = false;
    empty.textContent = "Could not load prescriptions: " + err.message;
    return;
  }

  list.innerHTML = "";
  empty.textContent = "No prescriptions saved yet. Add one above.";
  empty.hidden = currentPrescriptions.length > 0;

  currentPrescriptions.forEach((p) => {
    const li = document.createElement("li");
    li.className = "med-item";

    const info = document.createElement("div");
    info.className = "med-item-info";

    const title = document.createElement("strong");
    title.textContent = p.name + " (" + p.dosage + ")";

    const details = document.createElement("div");
    details.className = "text-muted";
    details.textContent =
      p.tablets + " tablet(s) · " + timesLabel(p.time) + " · " + p.frequency;

    const dates = document.createElement("div");
    dates.className = "text-muted";
    dates.textContent = p.startDate + " to " + p.endDate;

    info.appendChild(title);
    info.appendChild(details);
    info.appendChild(dates);

    const actions = document.createElement("div");
    actions.className = "med-item-actions";

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-secondary";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => startEdit(p));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn btn-danger";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => deletePrescription(p.id));

    actions.appendChild(editBtn);
    actions.appendChild(deleteBtn);

    li.appendChild(info);
    li.appendChild(actions);
    list.appendChild(li);
  });
}
