# Lead Scraper

A full stack lead generation and lead management application created from a real investment real estate prospecting workflow.

**Live Demo:**  
https://leadscraper2026.netlify.app/

## Why I Built It

My wife worked in investment real estate.

Part of the business involved finding local buyers and operators who might be interested in distressed properties.

That could include:

- Contractors
- Roofers
- Builders
- Investors
- Service businesses
- Other niche local operators

Finding those prospects manually was repetitive.

The original idea was straightforward:

> Search a business niche and location, collect potential leads, organize the information, and turn it into an outreach list.

That workflow became Lead Scraper.

## How the Project Evolved

The project began around Google Maps prospecting.

As I developed it further, it became a broader full stack lead management application.

The current application includes:

- User authentication
- Account scoped lead data
- Lead tables
- CSV import
- Data cleaning
- Deduplication
- Export workflows
- Background jobs
- Job progress
- Persistent storage
- API authorization
- Cloud deployment

The public version is structured as a safer portfolio demonstration rather than directly exposing the original scraping workflow.

## Current Demo Data

The current public search workflow uses **synthetic demonstration records**.

The application does not currently expose the original Google Places workflow as a production data source.

Commercial deployment with live search data would require an authorized and licensed provider.

Users can also work with CSV data they own or are authorized to use.

## Technology Stack

### Front End

- React 19
- TypeScript
- Vite
- Supabase JavaScript client
- Lucide React

### Backend

- Python
- FastAPI
- Uvicorn
- Beautiful Soup
- PyJWT
- HTTPX

### Authentication

- Supabase Auth
- Verified JWTs
- Account scoped access

### Data

Local development:

- SQLite

Production architecture:

- PostgreSQL
- Render database
- Background worker

### Testing

- Pytest
- Front end TypeScript checking
- Backend API tests

### Deployment

- Netlify
- Render
- Supabase
- GitHub

## Architecture

The deployed system is split between a React frontend and Python backend.

```text
Browser
  ↓
React + TypeScript
  ↓
Supabase Authentication
  ↓
Verified Access Token
  ↓
FastAPI
  ↓
Lead Services
  ↓
PostgreSQL
  ↓
Background Worker
```

Netlify hosts the frontend.

Render hosts the API, worker, and production PostgreSQL resources.

Supabase provides authentication.

## Authentication Flow

The frontend authenticates through Supabase.

Authenticated API requests include a token.

The FastAPI backend verifies that token before allowing access to protected application data.

Lead records are scoped to the authenticated account.

This keeps authorization enforcement in the backend rather than relying only on what the browser interface displays.

## Lead Workflow

A typical application workflow is:

```text
Authenticate
   ↓
Search or Import
   ↓
Create Lead Records
   ↓
Clean Data
   ↓
Deduplicate
   ↓
Store
   ↓
Review
   ↓
Export
```

Longer running operations can be processed through the background worker.

## CSV Workflow

The application supports importing lead data from authorized CSV files.

Imported data can move through cleaning and deduplication workflows before being stored and displayed.

This provides a useful workflow even when no external search provider is connected.

## Development

The repository contains separate frontend and backend applications.

### Run the Backend

From:

```text
backend/
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest -q
```

Start the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Run the Frontend

From:

```text
frontend/
```

Install dependencies:

```bash
npm install
```

Run the production build:

```bash
npm run build
```

Start the development server:

```bash
npm run dev
```

## Deployment Architecture

```text
GitHub
  │
  ├── Netlify
  │     └── React Frontend
  │
  └── Render
        ├── FastAPI
        ├── Worker
        └── PostgreSQL

Supabase
  └── Authentication
```

## Security Considerations

The current architecture includes:

- Backend token verification
- Account scoped records
- Restricted environment variables
- Separate frontend and backend credentials
- Sanitized publication workflow
- Secret scanning tools
- CORS configuration
- Clean GitHub publication tooling

Browser environment variables are limited to values intended to be public.

Service credentials and database secrets belong only in trusted server environments.

## Google API History

The original local scraper used a Google API credential that was exposed during development.

That credential is not included in the current public application source.

The project documentation requires revoking or rotating the original key and publishing only from a sanitized snapshot.

That experience influenced the current security and publication workflow.

## Important Limitations

The current public application is a precommercial portfolio MVP.

It does not currently include:

- A licensed live business data provider
- Billing
- Customer ready legal policies
- Complete rate limiting
- Production monitoring
- A complete data deletion workflow

The current public search experience uses synthetic records.

## Key Engineering Decisions

### Separate Frontend and Backend

The React interface and FastAPI application can be deployed and scaled independently.

### Backend Authorization

Protected data access is enforced by the API rather than trusting browser state.

### Background Processing

Longer running jobs can execute outside the request cycle.

### Synthetic Public Search

The public demo can demonstrate the workflow without relying on questionable scraping behavior or exposing third party API credentials.

### CSV Support

Users can work with data they own or are licensed to use even without a live search integration.

## What This Project Demonstrates

Lead Scraper demonstrates experience across:

- React
- TypeScript
- Python
- FastAPI
- API design
- Authentication
- JWT validation
- PostgreSQL
- Background workers
- Data processing
- CSV workflows
- Testing
- Security
- Netlify
- Render
- Supabase
- Full stack deployment

It also demonstrates how a small automation idea can evolve into a larger software product with authentication, persistence, asynchronous work, and cloud infrastructure.

## Portfolio

**Portfolio:**  
https://zieglercodes.netlify.app/

**GitHub:**  
https://github.com/ZieglerCodes

**LinkedIn:**  
https://www.linkedin.com/in/therealadamziegler/
