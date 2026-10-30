/* =========================================================
   MedGuard — dashboard.js
   Builds the "today" and "upcoming" medicine lists from the
   prescriptions stored in PostgreSQL (fetched via the FastAPI
   backend — see common.js for API_BASE_URL / apiRequest()).
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
  const patient = requirePatient();
  if (!patient) return; // requirePatient() already redirected

  document.getElementById("welcomeHeading").textContent =
    "Welcome, " + patient.name + "!";

  document.getElementById("logoutLink").addEventListener("click", function (e) {
    e.preventDefault();
    logoutPatient();
  });

  renderSchedules();
});

// Converts a prescription as returned by the API (medicine_name,
// strength, start_date, end_date) into the field names this page's
// rendering code uses (name, dosage, startDate, endDate).
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

// Turns "YYYY-MM-DD" strings into Date objects we can compare safely.
function toDate(dateStr) {
  return dateStr ? new Date(dateStr + "T00:00:00") : null;
}

function isActiveToday(prescription) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const start = toDate(prescription.startDate);
  const end = toDate(prescription.endDate);
  if (start && today < start) return false;
  if (end && today > end) return false;
  return true;
}

function isUpcoming(prescription) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const start = toDate(prescription.startDate);
  return start && start > today;
}

function timesLabel(times) {
  if (!times || times.length === 0) return "No time set";
  const order = ["morning", "afternoon", "evening", "night"];
  return order
    .filter((t) => times.includes(t))
    .map((t) => t.charAt(0).toUpperCase() + t.slice(1))
    .join(", ");
}

async function renderSchedules() {
  const patient = getCurrentPatient();
  const todayList = document.getElementById("todayList");
  const todayEmpty = document.getElementById("todayEmpty");
  const upcomingList = document.getElementById("upcomingList");
  const upcomingEmpty = document.getElementById("upcomingEmpty");

  let prescriptions = [];
  try {
    const apiPrescriptions = await apiRequest("/prescriptions/" + patient.id, {
      method: "GET",
    });
    prescriptions = apiPrescriptions.map(fromApiPrescription);
  } catch (err) {
    todayEmpty.hidden = false;
    todayEmpty.textContent = "Could not load your schedule: " + err.message;
    upcomingEmpty.hidden = true;
    return;
  }

  todayList.innerHTML = "";
  upcomingList.innerHTML = "";

  const today = prescriptions.filter(isActiveToday);
  const upcoming = prescriptions.filter(isUpcoming);

  todayEmpty.hidden = today.length > 0;
  upcomingEmpty.hidden = upcoming.length > 0;

  today.forEach((p) => {
    todayList.appendChild(buildMedItem(p));
  });

  upcoming.forEach((p) => {
    upcomingList.appendChild(buildMedItem(p, true));
  });
}

function buildMedItem(prescription, showStartDate) {
  const li = document.createElement("li");
  li.className = "med-item";

  const info = document.createElement("div");
  info.className = "med-item-info";

  const title = document.createElement("strong");
  title.textContent = prescription.name + " (" + prescription.dosage + ")";

  const details = document.createElement("div");
  details.className = "text-muted";
  details.textContent = showStartDate
    ? "Starts " + prescription.startDate + " · " + timesLabel(prescription.time)
    : timesLabel(prescription.time) +
      " · " +
      prescription.tablets +
      " tablet(s) · " +
      prescription.frequency;

  info.appendChild(title);
  info.appendChild(details);
  li.appendChild(info);

  return li;
}
