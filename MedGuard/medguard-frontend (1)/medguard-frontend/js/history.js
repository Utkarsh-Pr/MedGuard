/* =========================================================
   MedGuard — history.js
   Renders the list of past scans, fetched from the FastAPI
   backend's GET /history/{patient_id} endpoint (PostgreSQL
   scan_history table) instead of localStorage.
   ========================================================= */

const HISTORY_STATUS_LABELS = {
  ADVISORY_MATCH: { label: "ADVISORY MATCH", badgeClass: "badge-safe" },
  WRONG_MEDICINE: { label: "WRONG MEDICINE", badgeClass: "badge-danger" },
  WRONG_TIME: { label: "WRONG TIME", badgeClass: "badge-warning" },
  NOT_ON_LIST: { label: "NOT ON YOUR LIST", badgeClass: "badge-danger" },
  EXPIRED: { label: "EXPIRED", badgeClass: "badge-danger" },
  RETAKE_REQUIRED: { label: "RETAKE PHOTO", badgeClass: "badge-warning" },
  MANUAL_VERIFICATION: { label: "VERIFY MANUALLY", badgeClass: "badge-warning" },
};

document.addEventListener("DOMContentLoaded", function () {
  const patient = requirePatient();
  if (!patient) return;

  document.getElementById("logoutLink").addEventListener("click", function (e) {
    e.preventDefault();
    logoutPatient();
  });

  document.getElementById("closeDetailBtn").addEventListener("click", function () {
    document.getElementById("detailCard").hidden = true;
  });

  renderHistory();
});

function formatTimestamp(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString();
}

// Converts one scan_history row from the API (detected_medicine,
// safety_status, scan_time) into the field names this page's
// rendering code uses (medicineName, status, timestamp).
function fromApiHistoryEntry(apiEntry) {
  return {
    id: apiEntry.id,
    timestamp: apiEntry.scan_time,
    medicineName: apiEntry.detected_medicine || "Unknown",
    status: apiEntry.safety_status,
    confidence: apiEntry.confidence,
  };
}

async function renderHistory() {
  const patient = getCurrentPatient();
  const list = document.getElementById("historyList");
  const empty = document.getElementById("historyEmpty");

  let history = [];
  try {
    const apiHistory = await apiRequest("/history/" + patient.id, { method: "GET" });
    history = apiHistory.map(fromApiHistoryEntry);
  } catch (err) {
    list.innerHTML = "";
    empty.hidden = false;
    empty.textContent = "Could not load scan history: " + err.message;
    return;
  }

  list.innerHTML = "";
  empty.textContent = "No scans yet. Go to Scan Medicine to check your first one.";
  empty.hidden = history.length > 0;

  history.forEach((entry) => {
    const statusInfo = HISTORY_STATUS_LABELS[entry.status] || {
      label: entry.status,
      badgeClass: "badge-info",
    };

    const li = document.createElement("li");
    li.className = "med-item";

    const info = document.createElement("div");
    info.className = "med-item-info";

    const title = document.createElement("strong");
    title.textContent = entry.medicineName;

    const details = document.createElement("div");
    details.className = "text-muted";
    details.textContent = formatTimestamp(entry.timestamp);

    const badge = document.createElement("span");
    badge.className = "badge " + statusInfo.badgeClass;
    badge.textContent = statusInfo.label;
    badge.style.marginTop = "6px";
    badge.style.display = "inline-block";

    info.appendChild(title);
    info.appendChild(details);
    info.appendChild(badge);

    const actions = document.createElement("div");
    actions.className = "med-item-actions";

    const viewBtn = document.createElement("button");
    viewBtn.type = "button";
    viewBtn.className = "btn btn-secondary";
    viewBtn.textContent = "View Details";
    viewBtn.addEventListener("click", () => showDetail(entry, statusInfo));

    actions.appendChild(viewBtn);

    li.appendChild(info);
    li.appendChild(actions);
    list.appendChild(li);
  });
}

function showDetail(entry, statusInfo) {
  document.getElementById("detailDate").textContent = formatTimestamp(entry.timestamp);
  document.getElementById("detailMedicine").textContent = entry.medicineName;
  document.getElementById("detailResult").textContent = statusInfo.label;
  document.getElementById("detailConfidence").textContent = entry.confidence + "%";
  document.getElementById("detailCard").hidden = false;
  document.getElementById("detailCard").scrollIntoView({ behavior: "smooth" });
}
