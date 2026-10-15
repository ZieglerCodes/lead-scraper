"""Offline file/secret/config checks; runs with Python standard library only."""
from pathlib import Path
import sys, re, os, subprocess

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'backend/app/main.py','backend/app/auth.py','backend/app/db.py',
    'backend/app/postgres.py','backend/app/storage.py','backend/app/worker.py',
    'backend/app/jobs.py','backend/app/services/cleaning.py',
    'backend/app/services/pipeline.py','backend/app/services/sources.py',
    'backend/requirements.txt','backend/.env.example',
    'frontend/src/App.tsx','frontend/src/AuthGate.tsx','frontend/src/main.tsx',
    'frontend/src/lib/api.ts','frontend/src/lib/supabase.ts',
    'frontend/src/styles.css','frontend/package.json','frontend/.env.example',
    'frontend/vite.config.ts','render.yaml','netlify.toml',
    'tools/create_publish_snapshot.py','tools/scrub_legacy_key.py',
    'tools/verify_project.py','START_HERE.md','README_PHASE4.md',
]

def check():
    failed = []
    print(f'Project root: {ROOT}')
    for item in REQUIRED:
        if not (ROOT/item).is_file(): failed.append(item)
    if failed:
        print('MISSING REQUIRED FILES:')
        for item in failed: print('  -', item)
    else:
        print(f'OK: {len(REQUIRED)} required project files found.')
    if (ROOT/'lead-scraper'/'backend').is_dir():
        print('WARNING: Nested lead-scraper/lead-scraper detected. Follow START_HERE.md')
    for candidate in (ROOT/'google_scraper.py',ROOT/'legacy'/'google_scraper.py',ROOT/'legacy_reference'/'google_scraper.py'):
        if candidate.is_file():
            content=candidate.read_text(encoding='utf-8-sig',errors='replace')
            if "AIza" in content and "API_KEY" in content and "os.environ" not in content:
                print('SECURITY WARNING: A hardcoded Google API key was detected in',candidate)
                print('Do not publish the old script. Revoke the key in Google Cloud.')
    if (ROOT/'backend'/'.env').exists():
        print('Backend .env exists (content not displayed).')
    else:
        print('SETUP NEEDED: backend/.env (see START_HERE.md)')
    if (ROOT/'frontend'/'.env.local').exists():
        print('Frontend .env.local exists (content not displayed).')
    else:
        print('SETUP NEEDED: frontend/.env.local (see START_HERE.md)')
    print('Python:',sys.version.split()[0])
    try:
        p=subprocess.run(['node','--version'],capture_output=True,text=True,timeout=4)
        print('Node:',p.stdout.strip() if p.returncode==0 else 'not installed')
    except (FileNotFoundError,subprocess.TimeoutExpired): print('Node: not installed/not available')
    if failed:
        return 1
    return 0

if __name__=='__main__':
    sys.exit(check())
