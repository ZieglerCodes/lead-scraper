# Phase 4 changes

- Added Render deployment Blueprint and Netlify build config.
- Added Postgres implementation of owner-scoped jobs and leads and durable CSV job payloads.
- Added standalone worker that atomically claims jobs and marks stale interrupted jobs failed.
- Preserved SQLite development behavior; `DATABASE_URL` switches on production storage and processing.
- Added environment-aware DB health checks and limited per-user job creation (30/day, 3 active in PostgreSQL).
- Added safe source-only publishing snapshot creation to avoid pushing old key and prior history.
- Tests added for production queue API behaviors and worker job-handling logic.
- Disabled Google live scraping: only synthetic demo searches and authorized CSV imports.

**Unverified:** deployed Render services, paid account setup, live PostgreSQL transaction integration, Netlify npm build, real-world Supabase flows. Credentials and external accounts are NOT accessed or changed by this package.
