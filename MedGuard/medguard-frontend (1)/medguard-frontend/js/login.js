/* =========================================================
   MedGuard — login.js
   Handles the demo login / patient-selection form.
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("loginForm");
  const nameInput = document.getElementById("patientName");

  // If a patient is already selected, skip straight to the dashboard.
  const existing = getCurrentPatient();
  if (existing) {
    window.location.href = "dashboard.html";
    return;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const name = nameInput.value.trim();
    if (!name) return;

    const submitBtn = form.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Signing in…";

    try {
      // Demo login: the backend looks up a patient by name, or creates
      // one if it doesn't exist yet, and returns a real integer id —
      // that id is what prescriptions/scans/history are linked to.
      const patient = await apiRequest("/patients/login", {
        method: "POST",
        body: JSON.stringify({ name: name }),
      });
      saveData(STORAGE_KEYS.PATIENT, patient);
      window.location.href = "dashboard.html";
    } catch (err) {
      alert(err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = "Enter MedGuard";
    }
  });
});
