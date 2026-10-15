# Lead Scraper $0 Hosting Patch — Windows & GitHub

This update replaces Phase 4's **paid Render Blueprint** with one Render Free web service, using **Supabase Free Postgres** as the database and Supabase Auth for login. Frontend remains on **Netlify Free**. No separate Render worker/database is created.

> Suitable only for prototypes with short demo jobs and small authorized CSVs. HTTP-process background tasks can be lost if the free Render instance restarts, spins down, or a deploy interrupts a job. Jobs may be left queued/running; the user may need to retry. Do not use this processing model for heavy scraping or paying customers.

## A. Patch the GitHub publishing checkout, not your backup

1. Download and unzip the patch ZIP. Inside is a folder named `patch`.
2. Make a backup of `C:\Users\adamz\Desktop\SWE\lead-scraper-publish`.
3. Copy the **contents of `patch`** into `C:\Users\adamz\Desktop\SWE\lead-scraper-publish`, selecting **Replace** for the modified files. It must leave `render.yaml` at the root, `backend\app\main.py` and `backend\app\worker.py`, etc.
4. In PowerShell:

```powershell
cd 'C:\Users\adamz\Desktop\SWE\lead-scraper-publish'
git diff --stat
git status --short
```

5. Audit changes. Then:

```powershell
git add render.yaml FREE_HOSTING_SETUP.md backend/app/main.py backend/app/worker.py backend/app/postgres.py backend/tests/test_free_mode.py
git commit -m 'Support free hosting with one API and Supabase Postgres'
git push origin main
```

Optionally apply the same patch files to the original working folder `C:\Users\adamz\Desktop\SWE\lead-scraper` to keep it in sync; **do not overwrite** personal `backend\data`, `.env`, or `.env.local` files.

## B. Supabase Free

- Use the **same Supabase project** for Auth and the backend database.
- Open Supabase > your project > **Connect** > **Session pooler** (port 5432, IPv4). Copy the complete session-pooler PostgreSQL connection string. Render is IPv4-only for this use case; do not use the IPv6-only direct connection URL.
- Fill in your database password on your own machine/Render dashboard; keep this URL secret. Never put it in `frontend`, in a public link, or in GitHub.
- Ensure Supabase Auth uses an asymmetric JWT signing key; set email/password provider and redirects in Authentication settings.

## C. Render Free

- Dashboard > **New > Blueprint** > connect the GitHub repository. With this updated `render.yaml`, the plan should show **one Web Service, Free**. It must NOT include a worker or Render Postgres database.
- For environment prompts, provide:
  - `DATABASE_URL`: your Supabase **Session pooler** full PostgreSQL URI (SECRET)
  - `SUPABASE_URL`: your Supabase project URL (e.g., `https://project-ref.supabase.co`)
  - `FRONTEND_ORIGINS`: your Netlify site `https://YOUR-SITE.netlify.app` (no trailing slash). For initial creation before Netlify deploy, use a placeholder exact origin `https://example.invalid`, then replace after deploying Netlify.
- Blueprint automatically sets `DEPLOYMENT_MODE=production`, `LEAD_SCRAPER_JOB_MODE=inprocess`, `PYTHON_VERSION=3.12.7`.
- Review the preview **before deploy**. If it says any paid resource or plans, cancel.
- On deploy success, open `https://YOUR-RENDER-URL/api/health`; verify `storage=PostgreSQL`, `processing=in-process best effort`. A 503 likely means a database connection issue; inspect Render logs, not the public error message.

## D. Netlify Free

- New Project > Import GitHub repo. `netlify.toml` from existing project has `base=frontend`, `publish=dist`.
- Configure **frontend environment variables** in Netlify site configuration before production deploy:
  - `VITE_SUPABASE_URL`: Supabase project URL
  - `VITE_SUPABASE_PUBLISHABLE_KEY`: your public `sb_publishable_...` key
  - `VITE_API_BASE_URL`: Render URL (e.g. `https://your-service.onrender.com`), no trailing slash.
- Update Render `FRONTEND_ORIGINS` with the exact Netlify URL.
- Update Supabase Auth Site URL and Redirect URLs with your exact Netlify origin and paths as supported by the app.
- Test register/login, short demo jobs, and authorized CSV import; check that another user cannot access the first user's job records.

## Notes and limits

- This patch does **not** restore live Google scraping. Rotate/revoke your previously exposed API key in Google Cloud.
- Supabase Free has quotas (notably a 500 MB DB quota) and projects may pause after inactivity. Render Free sleeps after 15 minutes idle; the first request may take about one minute.
- Do NOT choose a Render Free PostgreSQL database for durable data: the free database expires after 30 days.
- No payments are required if you remain within free allowances and choose only free resources; monitor dashboards and billing settings to avoid surprises.
- If you want truly durable queues for paying customers, move back to a separate worker or managed async task system.
