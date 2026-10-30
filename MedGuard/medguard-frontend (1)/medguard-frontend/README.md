# MedGuard — Frontend

AI-Powered Medication Safety Assistant — plain **HTML / CSS / vanilla JavaScript**
frontend, no frameworks. Built simple, high-contrast, and large-text for elderly
and visually impaired users.

Now connected to the **medguard-backend** FastAPI + PostgreSQL API — see that
project's own README for how to set it up and run it.

## How to run

1. Start the backend first (see `medguard-backend/README.md`) — it must be
   running at `http://localhost:8000` before you use this frontend.
2. Open `index.html` in any modern browser (Chrome, Edge, Firefox).
   Double-click it, or serve the folder (e.g. VS Code "Live Server", or
   `python -m http.server`) if your browser blocks camera access on
   `file://` URLs.

> Note: camera access (`getUserMedia`) requires either `https://` or
> `localhost`. If you open the file directly (`file://`), the "Use Camera"
> button may not work in some browsers — use "Upload Photo" instead.

If your backend runs somewhere other than `http://localhost:8000`, change
the `API_BASE_URL` constant at the top of `js/common.js`.

## Pages

| Page | File | Purpose |
|---|---|---|
| Login / patient selection | `index.html` | Demo login — calls `POST /patients/login` |
| Dashboard | `dashboard.html` | Today's schedule, upcoming meds, scan shortcut |
| Prescription entry | `prescription.html` | Add/edit/delete prescriptions via the backend API |
| Scan medicine | `scan.html` | Upload photo or use camera, sent to `POST /scan` |
| Safety check result | `result.html` | Shows the result returned by `POST /scan` |
| Scan history | `history.html` | Past scans, from `GET /history/{patient_id}` |
| Settings | `settings.html` | Font size, high contrast, voice on/off |

## Where data lives now

- **Patients, prescriptions, and scan history** live in **PostgreSQL**,
  reached through the FastAPI backend (`login.js`, `prescription.js`,
  `dashboard.js`, `scan.js`, and `history.js` all call `apiRequest()` /
  `fetch()` — see `js/common.js`).
- A few small, purely local things still use the browser's `localStorage`
  (see `js/common.js` → `STORAGE_KEYS`), since they don't need a database:
  - `medguard_patient` — the currently logged-in patient's `{ id, name }`,
    as returned by the backend at login
  - `medguard_settings` — accessibility settings (font scale, contrast, voice)
  - `medguard_last_scan_image` / `medguard_last_result` — hands the just-taken
    photo and the backend's scan result from `scan.html` to `result.html`

## How the field names line up with the backend

The backend uses slightly different field names than this UI's own
variables (matching a typical database schema, e.g. `medicine_name` /
`start_date` instead of `name` / `startDate`). Each page that talks to the
API has a small `toApiPayload()` / `fromApiPrescription()` /
`fromApiHistoryEntry()` pair of functions that converts between the two,
so the HTML and the rest of the rendering code didn't need to change.

## Accessibility features

- Large text (20px base) and a settings page to scale it up to 160%
- High-contrast mode (black background, bright yellow/blue text)
- "Listen to Result" and a floating 🔊 button on every page using the
  browser's built-in `SpeechSynthesis` API
- Visible keyboard focus outlines, skip-to-content link, semantic HTML
- Reduced-motion respected (`prefers-reduced-motion`)
