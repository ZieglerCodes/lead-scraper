# LEAD SCRAPER — COMPLETE PROJECT: START HERE

**This is ONE consolidated package.** You do not need the older Phase 1/2/3/4 ZIPs or the separately supplied `create_publish_snapshot.py`.

The app contains a React + TypeScript dashboard, Supabase Auth login, FastAPI API with verified JWTs, SQLite local storage, Render PostgreSQL production storage, a Render worker, CSV import/cleaning/deduplication, account-scoped records, automated Python tests, Netlify/Render configuration, and clean GitHub publication scripts.

**Important limitation:** Search currently returns clearly labeled **synthetic demo records**. For real data, import a CSV you own or are licensed to use. The original Google Places exporter is not connected or authorized as a storage/export source. See `legacy_reference/` for sanitized historical reference scripts. Paid licensed data integration is a separate step before commercial launch.

## A. SAFETY FIRST — old Google API key

The Google credential present in the original `google_scraper.py` was exposed. This ZIP does not contain that key. You said you haven't fixed it yet, so:

1. Go to https://console.cloud.google.com/apis/credentials and select the old project.
2. Find the **old key** associated with your local original scraper. **Delete/revoke it** if no other app needs it. Otherwise rotate, update the other app, then revoke the old key. Review API metrics and billing.
3. After installation, run `py -3 .\tools\scrub_legacy_key.py` in the installed project. This sanitizes certain original local files. It does NOT revoke the cloud key or rewrite old Git history.
4. Never publish the old folder or its Git history. Always publish from a clean snapshot.

## B. INSTALL THE NEW RELEASE IN YOUR ACTUAL FOLDER

Your destination is `C:\Users\adamz\Desktop\SWE\lead-scraper`.

1. Download `lead_scraper_COMPLETE_project.zip` and **right-click > Extract All**.
2. Open the extracted folder. You should see **two items**: `INSTALL_UPDATE.py` and the folder `lead-scraper` (plus an installation guide).
3. Open **PowerShell in the extracted folder**, the one containing `INSTALL_UPDATE.py` (NOT in `frontend`).
4. Run:

   ```powershell
   py -3 .\INSTALL_UPDATE.py
   ```

   The installer copies source files into `C:\Users\adamz\Desktop\SWE\lead-scraper`, backs up source files it is about to replace to a timestamped sibling folder, and **never deletes** `.env`, `.env.local`, your CSVs, `backend/data`, `.venv`, `node_modules`, or the prior Git history. It will not move your older Google scraper into the public app. The archived `legacy_reference` folder includes sanitized scripts for reference only.

   Alternative: manually copy the **contents** of the extracted `lead-scraper` folder into the existing project root (no double-nesting). Backup your current folder first, and never delete personal data.

5. Verify from your installed project root:

   ```powershell
   cd "C:\Users\adamz\Desktop\SWE\lead-scraper"
   py -3 .\tools\verify_project.py
   Test-Path .\tools\create_publish_snapshot.py
   ```

   The final command must say `True`. If it says False, **do not move on to GitHub**; the files are still in the wrong location.

## C. RUN THE PYTHON API LOCALLY

From a PowerShell window:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper\backend"
py -3.12 --version  # If not installed, use: py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `py -3` finds Python 3.14 and dependencies fail to install, install Python 3.12 and replace `py -3 -m venv .venv` with `py -3.12 -m venv .venv` after safely moving the old virtual environment out of the way. Never share `backend/.env`.

Once running, health is at http://127.0.0.1:8000/api/health . The backend will not authorize protected endpoints until Supabase is configured. API docs are at http://127.0.0.1:8000/docs .

## D. SUPABASE CONFIGURATION (REQUIRED FOR LOGIN)

1. Open https://supabase.com/dashboard . Create or use a project.
2. Enable email/password authentication and, for this backend, an **asymmetric** JWT signing key (ES256 or RS256). Follow https://supabase.com/docs/guides/auth/signing-keys .
3. In your installed project, copy `backend/.env.example` to `backend/.env`; replace only `YOUR_PROJECT_REF` with your actual project reference. Keep `FRONTEND_ORIGINS` for local development.
4. Copy `frontend/.env.example` to `frontend/.env.local`; fill in the project URL and **publishable** (`sb_publishable_...`) key. Set `VITE_API_BASE_URL=http://127.0.0.1:8000`.
5. In Supabase Auth redirect URL settings, allow `http://127.0.0.1:5173/**` while testing. Keep email confirmation enabled if intended.
6. Restart the backend after editing `.env`, and frontend after editing `.env.local`.

Do not put a service-role/secret key, Google key, Render DATABASE_URL, or personal tokens in any `VITE_` browser variable.

## E. RUN THE REACT WEBSITE LOCALLY

Open a SECOND PowerShell window:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper\frontend"
node --version
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

Visit http://127.0.0.1:5173 . Sign up/log in. Run a DEMO search and import `sample-leads.csv` (authorized synthetic sample). Verify job status and CSV download.

## F. GENERATE YOUR SAFE PUBLISHING FOLDER FOR GITHUB

1. Stop using your old Git repository for publication if it ever tracked your exposed Google key.
2. From the installed project **root** (not frontend):

   ```powershell
   cd "C:\Users\adamz\Desktop\SWE\lead-scraper"
   py -3 .\tools\create_publish_snapshot.py
   ```

   This creates **`C:\Users\adamz\Desktop\SWE\lead-scraper-publish`**. The snapshot tool refuses to overwrite an existing publish folder; inspect it and rename the old snapshot before creating a newer one.

3. Inspect `lead-scraper-publish` for keys, `.env`, personal data, CSVs and old Git history. Do not include `legacy_reference`, `.venv` or databases. If files are clean, run:

   ```powershell
   cd "C:\Users\adamz\Desktop\SWE\lead-scraper-publish"
   git init
   git branch -M main
   git add .
   git status --short
   git commit -m "Initial Lead Scraper application"
   ```

4. Create a new **private, empty** GitHub repo at https://github.com/new. Then:

   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/lead-scraper-deploy.git
   git push -u origin main
   ```

Use your own GitHub username. Be sure Git is installed and authenticated first.

## G. DEPLOY THE APP TO RENDER AND NETLIFY

`render.yaml` and `netlify.toml` are already in the publishing snapshot.

1. Render at https://dashboard.render.com : create a **Blueprint** from the new repo, review monthly costs; it defines **paid** web, background worker and PostgreSQL resources. Set `SUPABASE_URL` and initially `FRONTEND_ORIGINS=https://example.invalid` when prompted. Wait for API and worker services to become healthy. Copy Render web URL.
2. Netlify at https://app.netlify.com : import same repo. Base `frontend`, build `npm run build`, publish `dist` (all covered by `netlify.toml`). Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, and `VITE_API_BASE_URL=https://YOUR_RENDER_API.onrender.com`. Deploy and copy actual Netlify URL.
3. In Render API environment update `FRONTEND_ORIGINS=https://YOUR_NETLIFY_SITE.netlify.app`. Redeploy/restart API if necessary.
4. In Supabase Auth > URL Configuration set the Site URL and Redirect URLs to permit your **actual** Netlify domain, e.g. `https://YOUR_NETLIFY_SITE.netlify.app/**`.
5. From a new account, test registration, login, demo search, CSV import and job progress. Register a second account and verify it cannot access first account records. Ensure the worker processes jobs and Render `/api/health` reports PostgreSQL.

**Important:** The cloud database starts empty; previous local SQLite records are not migrated automatically. This is still a pre-commercial MVP: no billing, real licensed search provider, data deletion workflow, full rate limiting, monitoring, or customer-ready legal policies.

## H. COMMON ERRORS

- `can't open file ... frontend\\tools\\create_publish_snapshot.py` => You are in the wrong folder; `cd` to project root.
- `Test-Path ... create_publish_snapshot.py` -> `False` => You extracted/copied to wrong location. Run the installer from the extracted top folder.
- `Supabase not configured` => Create both environment files; restart API and React server.
- `npm not recognized` => Install current Node.js 22 LTS; restart PowerShell.
- CORS error => Add **exact Netlify origin** to `FRONTEND_ORIGINS`; no wildcard.
- Cloud jobs stay `queued` => Check Render **worker** service and PostgreSQL connectivity.
- `No module named ...` => Ensure packages were installed in `backend/.venv`.
- Search returns DEMO => Expected. Licensed live data integration has not been built.

## I. INCLUDED FILES

- `backend/` FastAPI endpoints, verified auth, SQLite dev store, PostgreSQL store, worker, CSV services and tests.
- `frontend/` React/Vite/TypeScript website, Supabase login, dashboard and lead tables.
- `tools/create_publish_snapshot.py` generates safe GitHub source folder.
- `tools/scrub_legacy_key.py` sanitizes original local script assignments.
- `tools/verify_project.py` verifies deployment source completeness.
- `render.yaml`, `netlify.toml` cloud deployment declarations.
- `legacy_reference/` seven original Python scripts, with exposed key redacted, **not** for public GitHub.
- Documentation: `README_PHASE2.md`, `README_PHASE3.md`, `README_PHASE4.md`, `START_HERE.md`, `SECURITY_ROTATION.md`, and changelogs.
