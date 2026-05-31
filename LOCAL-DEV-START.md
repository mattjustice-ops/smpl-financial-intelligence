# Local dev — one path to start the operating dashboard

Use **only** these steps, in order. Project folder:

`C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence`

---

## Before you begin

1. **Docker Desktop** is running (whale icon in the system tray).
2. **Node.js** and **Python 3.11+** are installed.

---

## Step 1 — Open PowerShell and go to the project

Copy and paste this entire block, then press Enter:

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
```

---

## Step 2 — Run the one startup script

Copy and paste this entire block, then press Enter. Wait until it finishes (it may take 1–2 minutes):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\START-HERE.ps1
```

**What this script does:**

- Stops old processes on ports **8000** and **3002**
- Runs `docker compose up -d` for Postgres
- Runs database migrations
- Confirms Management P&L routes exist in code (`management-pl-v4-inline`)
- Opens a **Backend** PowerShell window (`start-api.ps1`)
- Waits until `http://127.0.0.1:8000/api/v1/management-pl/ping` works
- Opens a **Frontend** PowerShell window (`npm run dev`)

If the script prints **ERROR** and exits, read the message, fix that issue, and run Step 2 again. Do not open the dashboard until Step 3 passes.

---

## Step 3 — Confirm the API (required)

In **Chrome or Edge**, open this URL:

http://127.0.0.1:8000/api/v1/management-pl/ping

You **must** see JSON like this (build id is the important part):

```json
{
  "status": "ok",
  "build": "management-pl-v4-inline",
  "main_file": "C:\\Users\\mattj\\.cursor\\projects\\empty-window\\saas-financial-intelligence\\backend\\app\\main.py"
}
```

If you see `{"detail":"Not Found"}` instead:

1. Look at the **Backend** terminal window for red Python errors.
2. Close that window.
3. Run Step 2 again.

Also open:

http://127.0.0.1:8000/health

You should see `"build": "management-pl-v4-inline"` and `"management_pl": true`.

---

## Step 4 — Open the dashboard

1. Check the **Frontend** terminal — wait until it says **Ready**.
2. Open:

http://localhost:3002

3. Expand **Workspace · data upload & API health** at the top — API health should be green.
4. Go to the **Management P&L** tab.

---

## Step 5 — If Management P&L still errors

In the browser, open:

http://localhost:3002/api/v1/management-pl/ping

You should see the same `management-pl-v4-inline` JSON as Step 3.

- If **Step 3 works** but **this URL fails**: restart the frontend window (Ctrl+C, then `npm run dev` in the frontend folder).
- If **both fail**: the backend window is not running this project — run Step 2 again.

---

## First-time only (if Step 2 says “No backend venv”)

Run this once, then run Step 2 again:

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
powershell -ExecutionPolicy Bypass -File .\scripts\START-HERE.ps1
```

---

## Stopping everything

Press **Ctrl+C** in the Backend and Frontend terminal windows, then:

```powershell
cd C:\Users\mattj\.cursor\projects\empty-window\saas-financial-intelligence
docker compose down
```

---

## Quick reference

| Service   | URL |
|-----------|-----|
| Dashboard | http://localhost:3002 |
| API health | http://127.0.0.1:8000/health |
| Management P&L ping | http://127.0.0.1:8000/api/v1/management-pl/ping |
| API docs | http://127.0.0.1:8000/docs |
