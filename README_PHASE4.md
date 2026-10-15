# Lead Scraper — Phase 4 deployment and Windows installation

**Project:** `C:\Users\adamz\Desktop\SWE\lead-scraper`  
**This package is SOURCE CODE, not a site that has already been deployed.** To make the website live, you must connect accounts at Google Cloud, GitHub, Supabase, Render and Netlify. The old Google Places export script is **not** used by the hosted app.

## What changed in Phase 4

- Netlify deployment configuration in `netlify.toml` (Vite/React frontend).
- Render Blueprint in `render.yaml`: FastAPI web service, separate always-on background worker, shared PostgreSQL database.
- `backend/app/postgres.py`: PostgreSQL data store, user-isolated jobs/leads, job limits, CSV payload storage in the DB until processed, atomic completion.
- `backend/app/worker.py`: database-backed polling worker; competing workers safely claim jobs with `FOR UPDATE SKIP LOCKED`; jobs interrupted long enough are marked failed and can be re-submitted.
- `backend/app/storage.py`: automatically selects PostgreSQL when `DATABASE_URL` exists or local SQLite when it doesn't.
- API behavior: POST jobs return queued immediately on PostgreSQL; worker processes them later; `/api/health` probes database readiness.
- `tools/create_publish_snapshot.py`: exports a new, safe, source-only folder (`lead-scraper-publish`) without old `.git` history, credentials, original scraper, SQLite DB, env files, or node_modules.
- Existing login, account registration, CSV import, synthetic search, job history, and lead explorer stay in place.

**Not included**: live Google search, paid lead-data license, payments, self-serve data deletion, migration from SQLite to PostgreSQL, full billing/abuse protections, scheduled backups, production external monitoring, complete legal policies, or an already connected Supabase project. Do not sell access to customers yet.

---

## STEP 0 — Google Cloud API key: do this before publishing anything

You said you **have not done anything to the old Google API key**. The original `google_scraper.py` contains an exposed credential. The Phase 4 app **does not need any Google API key**. The safest option if no other system uses that key is to **DELETE the old key**:

1. Sign in to **https://console.cloud.google.com/apis/credentials**.
2. Switch to the Cloud project that contains your Google Places/Maps API key.
3. Identify the exposed key from your original `google_scraper.py` locally; never paste its value into a message or GitHub.
4. Click the key and **Delete** it, confirming the operation. **This will disable all applications using that exact key.** If some other app still needs it, choose **Rotate key** instead: create a replacement, restrict it by API and application, migrate the other app, then **Delete the previous key**.
5. Review **APIs & Services > Metrics** and **Billing > Reports** for suspicious usage. Configure Cloud Billing budget/alerts and relevant quotas.
6. DO NOT create or paste a new Google key into this project. It will run demo searches and authorized CSV imports without one.

Official reference: https://docs.cloud.google.com/docs/authentication/api-keys

**Also scrub your LOCAL original scripts after extracting the ZIP**:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper"
py -3 .\tools\scrub_legacy_key.py
```

This script removes a simple hardcoded `API_KEY = "..."` assignment from `google_scraper.py` and `legacy/google_scraper.py` if present. It does **not** revoke credentials, inspect every backup, or remove old Git commits. Do not push historical Git commits containing the key.

---

## STEP 1 — Back up your EXISTING folder and database

1. Close any running Python backend or frontend development terminal.
2. Open Windows File Explorer and go to:

   `C:\Users\adamz\Desktop\SWE\`

3. Copy the **entire** `lead-scraper` folder. Rename the copy to `lead-scraper-backup-before-phase4`.
4. The backup is private and may include your OLD API key and `.env` files. Keep it off GitHub and shared/cloud public folders. Revoke the old key first.
5. If you already have data in `lead-scraper\backend\data\lead_scraper.sqlite3`, it will be preserved in the original project and your private backup. **The cloud PostgreSQL database starts empty**; there is no automatic SQLite data migration. Export authorized leads and re-import into your signed-in account as needed.

---

## STEP 2 — EXACT instructions for the downloaded ZIP

The downloadable file is named `lead_scraper_phase4_deployable.zip`. It contains one top-level folder named `lead-scraper`.

1. Download `lead_scraper_phase4_deployable.zip` to Windows Downloads.
2. Right-click the ZIP > **Extract All**. Windows generally creates:

   `C:\Users\adamz\Downloads\lead_scraper_phase4_deployable\lead-scraper\`

   (If you chose a different extraction location, use that actual location.)
3. **Open the extracted `lead-scraper` folder**. You should see `backend`, `frontend`, `tools`, `render.yaml`, `netlify.toml`, `README_PHASE4.md`, etc.
4. Select **the CONTENTS of that folder**, not the enclosing `lead-scraper` folder. Copy the contents.
5. Open your EXISTING project folder:

   `C:\Users\adamz\Desktop\SWE\lead-scraper\`

6. Paste. When Windows prompts about file conflicts, select **Replace files in the destination** for the package's application source files.
7. **DO NOT** remove `backend\data`, `backend\.env`, `frontend\.env.local`, `backend\.venv`, personal CSVs, or unrelated working files. The package contains `.env.example`, not your real secrets.
8. Verify these exact files exist:

```
C:\Users\adamz\Desktop\SWE\lead-scraper\
    README_PHASE4.md
    render.yaml
    netlify.toml
    backend\app\postgres.py
    backend\app\worker.py
    backend\app\storage.py
    backend\app\main.py
    backend\requirements.txt
    frontend\src\App.tsx
    frontend\package.json
    tools\create_publish_snapshot.py
    tools\scrub_legacy_key.py
```

**The WRONG structure** is `C:\Users\adamz\Desktop\SWE\lead-scraper\lead-scraper\backend\...` (accidentally adding an extra nesting level). Fix that before proceeding.

---

## STEP 3 — Scrub the old key and test the updated code locally

Open **PowerShell**:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper"
py -3 .\tools\scrub_legacy_key.py
cd .\backend
```

If Phase 3's Python virtual environment is already present, reuse it; otherwise create it:

```powershell
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -3 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The packaging environment passed **18 Python unit/API tests**. Your local install needs to reproduce those results. PostgreSQL live integration was **not** tested against an actual database in the packaging environment.

Then start backend locally (requires your existing `backend\.env` Supabase URL from Phase 3):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/api/health . Expected `phase: 4`, `storage: Local SQLite` when `DATABASE_URL` is not configured.

In a second PowerShell terminal:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper\frontend"
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

The local website is http://127.0.0.1:5173 . If you haven't configured Supabase yet, it will prompt you to connect it; do STEP 5. **The React production build has not been verified in the packaging environment** because npm package installation was unavailable; run `npm.cmd run build` locally before deployment.

---

## STEP 4 — Create a completely clean GitHub publishing folder

Do **not** push your original `lead-scraper` directory with its old Git history, original Google scraper, or local secret files. Create a source-only snapshot:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper"
py -3 .\tools\create_publish_snapshot.py
```

This creates a **sibling** folder:

`C:\Users\adamz\Desktop\SWE\lead-scraper-publish`

The script stops rather than overwriting if that folder already exists. Review the contents before publishing. It has no `.git` folder, Google scraper, `legacy`, `.env`, `node_modules`, or SQLite database. Repeat the clean publishing process for subsequent releases by reviewing/removing or renaming the previous publish snapshot first, **after preserving any changes in it**.

Initialize a **NEW** Git repo there:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper-publish"
git init
git branch -M main
git add .
git status --short
git commit -m "Build Phase 4 hosted lead scraper"
```

**Review `git status --short` before the commit**. If any key or local data is visible, STOP, remove it and verify again.

At https://github.com/new create an **empty PRIVATE repo** named `lead-scraper-deploy`. Do not initialize README/license/gitignore on GitHub. Then run (replace USERNAME):

```powershell
git remote add origin https://github.com/USERNAME/lead-scraper-deploy.git
git push -u origin main
```

Use GitHub's normal sign-in/authentication prompt. Do not paste a personal access token or any API secret into scripts. GitHub private code still needs normal secret hygiene; private is not a substitute for cleaning the history.

---

## STEP 5 — Configure Supabase (this also covers skipped Phase 3 setup)

1. Open https://supabase.com/dashboard, select your existing Phase 3 project OR create a new one.
2. From project **Connect / API settings** copy the **Project URL** and the **publishable key** (`sb_publishable_...`). Publishable keys are designed for frontend use. DO NOT use `sb_secret_`, `service_role`, or your database password.
3. Under **Authentication > Providers > Email**, enable email/password and email confirmation.
4. Under **Authentication > Signing Keys**, use an active **asymmetric** signing key (`ES256` recommended or `RS256`). The backend verifies the issuer-specific JWKS. Legacy `HS256` sessions are rejected by this project.
5. Leave the Auth redirect configuration open; we'll insert the actual Netlify domain in STEP 8.
6. For a private beta, **disable "Allow new users to sign up" after you have created your own account**, or invite your intended test users through Supabase. This reduces uninvited access. Confirm Email should stay enabled.

Official signing-key docs: https://supabase.com/docs/guides/auth/signing-keys

---

## STEP 6 — Deploy the Render backend, PostgreSQL, and worker

**This is a billed deployment.** The blueprint has TWO paid compute services (`0.5c-512mb` API and worker), and a small paid PostgreSQL instance (`0.1c-256mb`). Check https://render.com/pricing and review Render's actual checkout estimate before confirming. Do not create paid infrastructure if you're not ready for recurring charges.

1. Open https://dashboard.render.com .
2. Select **New > Blueprint** (sometimes labelled `Blueprints`).
3. Connect GitHub and select your **new** `lead-scraper-deploy` repository.
4. Render detects root-level `render.yaml` and previews THREE resources: `lead-scraper-api`, `lead-scraper-worker`, `lead-scraper-postgres`.
5. Review plans, billing, and deploy settings. If Render asks for environment variables marked `sync: false`, set:

   - `SUPABASE_URL` = `https://YOUR_PROJECT_REF.supabase.co`
   - `FRONTEND_ORIGINS` = `https://example.invalid` **TEMPORARILY**, until Netlify assigns your real HTTPS domain. This placeholder denies browser access from other origins rather than using `*`.

6. Confirm the Blueprint deployment when you're ready to be billed. The worker and API are connected to the same PostgreSQL database through injected `DATABASE_URL`; **do not paste or publish that database URL**.
7. When `lead-scraper-api` is Live, copy its unique URL, e.g. `https://lead-scraper-api-xxxx.onrender.com`. Yours may differ.
8. Visit `https://YOUR_ACTUAL_RENDER_API_URL/api/health`. It must return JSON with `status: ok`, `phase: 4`, `storage: PostgreSQL`, `processing: durable worker`.
9. Confirm `lead-scraper-worker` shows **Running** in Render logs. The API alone will not process cloud jobs without this worker.

If the web server is unhealthy: check Render logs and ensure the PostgreSQL resource is ready and `DATABASE_URL` is injected. Worker logs can reveal processing errors. If Blueprint resource names already exist, choose unique names and keep the `fromDatabase` references consistent.

Official Blueprint docs: https://render.com/docs/blueprint-spec

---

## STEP 7 — Deploy the frontend on Netlify

1. Open https://app.netlify.com .
2. Choose **Add new project > Import an existing project**; select GitHub and the **new** `lead-scraper-deploy` repository.
3. Netlify detects root `netlify.toml`: build base **frontend**, build command **npm run build**, publish directory **dist** (relative to base). Verify these match if prompted.
4. Before you deploy, set these **three site environment variables** under site build/environment configuration:

   - `VITE_SUPABASE_URL` = the same `https://YOUR_PROJECT_REF.supabase.co`
   - `VITE_SUPABASE_PUBLISHABLE_KEY` = your Supabase `sb_publishable_...` key
   - `VITE_API_BASE_URL` = your actual Render API URL, `https://...onrender.com`, **without `/api` at the end**.

5. Start the deployment. Check the build log for success. A failed frontend build is NOT a successfully deployed Phase 4.
6. Copy the assigned HTTPS Netlify URL, e.g. `https://lead-scraper-yourname.netlify.app`.
7. At first, your browser may get a CORS error because the backend still has `FRONTEND_ORIGINS=https://example.invalid`. The next step fixes that.

Remember: **EVERY** `VITE_...` value is embedded in public browser JavaScript. Only the Supabase publishable key is appropriate; never place secrets or Google keys there.

Official Vite/Netlify docs: https://docs.netlify.com/build/frameworks/framework-setup-guides/vite/

---

## STEP 8 — Connect the domain to Render and Supabase

**Render:** Open the **web API service** > **Environment** and change:

`FRONTEND_ORIGINS=https://YOUR-ACTUAL-NETLIFY-SITE.netlify.app`

No trailing slash; no wildcards; comma-separate only if you have additional exact trusted origins (e.g. local development). Save and deploy/restart the API as Render instructs. Confirm with browser developer tools that requests are not blocked by CORS.

**Supabase:** Open your project's **Authentication > URL Configuration**:

- **Site URL**: `https://YOUR-ACTUAL-NETLIFY-SITE.netlify.app`
- **Redirect URLs**: add `https://YOUR-ACTUAL-NETLIFY-SITE.netlify.app/**`
- If you still develop locally, retain `http://127.0.0.1:5173/**` and `http://localhost:5173/**` as allowed development redirects only.

Go back to Netlify and refresh your URL. Sign up, confirm your email, and sign in. To keep this as a private tool, turn off public new signups in Supabase **after** your own account is created, and invite specific additional testers.

---

## STEP 9 — Production smoke tests

| Test | Expected outcome |
|---|---|
| Open Netlify homepage | Login screen appears; no anonymous lead access |
| Check Render `/api/health` | `phase: 4`, `PostgreSQL`, `durable worker` |
| Open API `/api/jobs` without bearer token | HTTP 401 |
| Sign in with Account A | Authenticated dashboard loads |
| Run demo `Roofers` / `Houston, TX` | Job queued, then completed, synthetic lead records visible |
| Upload `sample-leads.csv` you are authorized to import | Job completed, CSV results visible |
| Export only authorized CSV-origin leads | File downloads correctly |
| Sign out and sign in as Account B | Account B has independent jobs/history; cannot view A's job ID |
| Check Render worker logs | Job IDs processed without exceptions |
| View Google Cloud Credentials | Previously exposed key is deleted/disabled |

If a job remains `queued`, check whether the worker is running. If it moves to `failed`, examine Render worker logs. If login works but calls to API fail, recheck Netlify `VITE_API_BASE_URL`, Render `FRONTEND_ORIGINS`, and Supabase `SUPABASE_URL`/signing keys.

**Storage and data caveats:** Existing local SQLite records are not automatically copied into PostgreSQL. To import authorized lead records, export a suitable CSV from your old application and upload under the correct signed-in user on the deployed site. Do not migrate restricted Google Places content. Supabase users authenticate with the same project; switching Supabase projects changes account identities.

---

## STEP 10 — Before inviting actual customers

Phase 4 makes a **small private beta deployable**, not a mature commercial SaaS. Before broad/public signups you still need: a genuinely licensed source for exported leads; privacy/terms and user deletion/export workflows; verified email delivery; operational backups and restore drill; monitoring/alerts; mature rate limiting including IP-based controls; domain and account-abuse controls; formal schema migrations; proper scheduled security/dependency updates; integration tests against live PostgreSQL and Supabase; and a system for preventing unexpected paid usage.

If you use Google Maps Platform later, do not simply switch the original Places-to-CSV script back on; verify data licensing, storage and display restrictions first: https://developers.google.com/maps/documentation/places/web-service/policies .

### Troubleshooting commands

From **your local project**:

```powershell
cd "C:\Users\adamz\Desktop\SWE\lead-scraper\backend"
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm.cmd run build
```

To regenerate a clean deployment snapshot for a new push, create a **new snapshot after reviewing/removing the old** `lead-scraper-publish` folder. Never push original Git history or the legacy Google script.
