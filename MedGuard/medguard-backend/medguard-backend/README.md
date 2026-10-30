# MedGuard Backend

A simple FastAPI + PostgreSQL backend for the MedGuard frontend.
Built to be easy to read and explain in a college major-project viva —
no microservices, no Docker, no complex architecture.

## Project structure

```
medguard-backend/
│
├── main.py           # FastAPI app: all API endpoints + AI pipeline orchestration
├── database.py        # PostgreSQL connection (SQLAlchemy engine/session)
├── models.py           # ORM table definitions (patients, prescriptions, scan_history)
├── schemas.py           # Pydantic request/response validation
├── crud.py               # Functions that read/write the database
├── ai/
│   ├── classifier.py      # Dummy CNN medicine classifier (replace later)
│   ├── ocr.py               # Dummy OCR: dosage + expiry extraction (replace later)
│   └── image_quality.py      # Dummy OpenCV blur/quality check (replace later)
├── uploads/                    # Uploaded scan photos are saved here
├── .env                          # Your real database credentials (not committed)
├── .env.example                    # Template showing the DATABASE_URL format
├── requirements.txt                  # Python dependencies
└── README.md                           # This file
```

## How each file works (for your viva)

- **database.py** — reads `DATABASE_URL` from `.env` and creates the
  SQLAlchemy `engine`/`SessionLocal`. `get_db()` is a small FastAPI
  dependency that hands each request a database session and closes it
  afterwards.
- **models.py** — one Python class per table (`Patient`, `Prescription`,
  `ScanHistory`). SQLAlchemy turns these into real PostgreSQL tables via
  `Base.metadata.create_all()`, called once at startup in `main.py`.
- **schemas.py** — Pydantic models describing exactly what JSON shape
  each endpoint accepts and returns. FastAPI uses these to validate
  incoming requests and to build the Swagger docs automatically.
- **crud.py** — the actual database queries (create/read/update/delete),
  kept separate from the API layer so `main.py` stays short.
- **ai/classifier.py, ai/ocr.py, ai/image_quality.py** — the three
  stages of the medicine-scanning pipeline. Each currently returns
  real CPU inference pipeline. The classifier returns `unknown` until
  its trained ONNX model and calibrated thresholds are installed; it
  never substitutes a random prediction.
- **main.py** — defines every API endpoint, wires CORS so the browser
  frontend can call it, and contains `process_medicine_image()` (calls
  the three `ai/` modules in order) and `evaluate_safety()` (the
  rule-based comparison against the patient's saved prescriptions).

## 1. Install PostgreSQL and create the database

If you don't already have PostgreSQL installed, install it first
(postgresql.org, or `sudo apt install postgresql` on Ubuntu).

Then open a terminal and create the database:

```bash
# Log in to PostgreSQL as the postgres superuser
psql -U postgres

# Inside the psql prompt, create the database:
CREATE DATABASE medguard;

# (optional) exit psql
\q
```

If you'd rather use a GUI tool (pgAdmin, DBeaver, etc.), just create a
new database named `medguard` — same result.

## 2. Set your database credentials

Copy the example file and edit it:

```bash
cp .env.example .env
```

Open `.env` and put in **your own** PostgreSQL username and password:

```
DATABASE_URL=postgresql://<your_username>:<your_password>@localhost:5432/medguard
```

For example, if you log in to PostgreSQL as `postgres` with password
`mypassword123`:

```
DATABASE_URL=postgresql://postgres:mypassword123@localhost:5432/medguard
```

## 3. Install Python dependencies

It's good practice to use a virtual environment first:

```bash
cd medguard-backend
python -m venv venv

# Activate it:
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

## 4. Start the backend

```bash
uvicorn main:app --reload
```

You should see output ending with something like:
`Uvicorn running on http://127.0.0.1:8000`

The three tables (`patients`, `prescriptions`, `scan_history`) are
created automatically the first time this runs — you don't need to
write any SQL yourself.

## 5. Open the interactive API docs (Swagger)

With the server running, open this in your browser:

```
http://localhost:8000/docs
```

This gives you a page where you can try every endpoint directly —
useful for testing before connecting the frontend, and great to show
in a viva.

## 6. Run the frontend against this backend

Open the MedGuard frontend's `index.html` as before (see the
frontend's own README). Its JavaScript now calls
`http://localhost:8000` for prescriptions, scans, and history — so
just make sure this backend is running first.

## Sample API requests

**Log in / select a patient:**
```bash
curl -X POST http://localhost:8000/patients/login \
  -H "Content-Type: application/json" \
  -d '{"name": "Meera Sharma"}'
```

**Add a prescription:**
```bash
curl -X POST http://localhost:8000/prescriptions \
  -H "Content-Type: application/json" \
  -d '{
        "patient_id": 1,
        "medicine_name": "Metformin",
        "strength": "500 mg",
        "tablets": 1,
        "time": ["morning", "night"],
        "frequency": "Twice daily",
        "start_date": "2026-09-01",
        "end_date": "2026-12-01"
      }'
```

**List a patient's prescriptions:**
```bash
curl http://localhost:8000/prescriptions/1
```

**Scan a medicine photo:**
```bash
curl -X POST http://localhost:8000/scan \
  -F "patient_id=1" \
  -F "image=@/path/to/photo.jpg"
```

**View scan history:**
```bash
curl http://localhost:8000/history/1
```

## Training and deploying the medicine model

The model is deliberately closed-set: an image is a catalog medicine only when
both calibrated confidence and prediction-margin gates pass. Otherwise the API
returns `MANUAL_VERIFICATION`.

1. Follow [`data/README.md`](data/README.md) to audit the raw image folders and
   create group-level train/validation/test manifests.
2. Install `requirements-training.txt`, then run
   `python scripts/train_classifier.py data/manifests/train.csv data/manifests/validation.csv data/manifests/test.csv`.
3. Add out-of-catalog photos to `Pharmassist Dataset/unknown`, score known and
   unknown images with `scripts/score_unknown.py`, then run
   `python scripts/calibrate_unknown.py scores.csv models/calibration.json`.
   This chooses thresholds which keep unknown false acceptance at or below 3%.
4. Deploy `models/medicine_classifier.onnx`, `models/labels.json`, and
   `models/calibration.json` together. See [`models/README.md`](models/README.md).

OCR uses English PaddleOCR and extracts raw text, brand, strength, expiry, and
batch number with deterministic parsing. The safety decision only returns an
`ADVISORY_MATCH` when quality, OCR, classifier, expiry, prescription, and time
all agree; it is not medical authorization.
