"""Generate a clean Phase 4 source-only folder for a NEW GitHub repo.

Never copies legacy scripts, original .git history, local databases, .env,
private keys, node_modules, or other unreviewed files. Deliberately fail
if destination already exists so we cannot silently overwrite user data.
"""
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
target = root.parent / 'lead-scraper-publish'
if target.exists():
    print(f'REFUSING: {target} exists. Review/remove or rename it first.')
    sys.exit(1)

files = [
    '.gitignore', 'render.yaml', 'netlify.toml', 'README_PHASE4.md', 'CHANGELOG_PHASE4.md',
    'START_HERE.md', 'sample-leads.csv', 'tools/verify_project.py', 'tools/create_publish_snapshot.py', 'backend/requirements.txt', 'backend/.env.example', 'backend/README.md',
    'frontend/.env.example', 'frontend/README.md', 'frontend/index.html',
    'frontend/package.json', 'frontend/tsconfig.json', 'frontend/vite.config.ts',
]
folders = ['backend/app', 'backend/tests', 'frontend/src']

def safe_copy(src, dst):
    if src.suffix in ('.db', '.pem', '.key') or src.name.endswith(('.sqlite3', '.pyc')):
        return
    if src.name.startswith('.env') and src.name != '.env.example':
        return
    if '__pycache__' in src.parts or 'node_modules' in src.parts:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src,dst)

for f in files:
    safe_copy(root / f, target / f)
for folder in folders:
    for src in (root / folder).rglob('*'):
        if src.is_file():
            safe_copy(src, target / src.relative_to(root))
print('Created source-only publication folder:', target)
print('Review all its contents before publishing. Never copy original google_scraper.py or legacy/.')
