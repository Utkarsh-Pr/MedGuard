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
