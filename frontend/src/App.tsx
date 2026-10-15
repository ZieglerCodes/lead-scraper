import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react'
import {
  Activity, AlertCircle, ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpRight, Check,
  CheckCircle2, ChevronDown, ChevronRight, CircleHelp, Clock3, Database, FileSpreadsheet,
  FileUp, Filter, Globe2, HardDrive, LayoutDashboard, ListChecks, LoaderCircle, Menu,
  Play, Plus, Radar, RefreshCw, Search, Server, Settings2, ShieldAlert, Sparkles, Terminal,
  UploadCloud, Users, X, Zap, type LucideIcon,
} from 'lucide-react'
import { api, API_BASE, type Health, type Job, type Lead } from './lib/api'
import { supabase } from './lib/supabase'
import type { User } from '@supabase/supabase-js'
import { LogOut } from 'lucide-react'
import { downloadJobCsv } from './lib/export'

type Page = 'overview' | 'search' | 'leads' | 'jobs' | 'import' | 'settings'
type NavLink = { page: Page; label: string; icon: LucideIcon }
const primaryNav: NavLink[] = [
  { page: 'overview', label: 'Overview', icon: LayoutDashboard },
  { page: 'search', label: 'Lead search', icon: Radar },
  { page: 'leads', label: 'Lead explorer', icon: Users },
  { page: 'jobs', label: 'Job history', icon: ListChecks },
  { page: 'import', label: 'Import CSV', icon: FileUp },
]
const PAGE_SIZE = 100
const dateFormat = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
const niceDate = (date: string) => { const parsed = new Date(date); return Number.isNaN(parsed.getTime()) ? '—' : dateFormat.format(parsed) }
const niceName = (job: Job) => job.kind === 'csv-import' ? 'CSV import' : (job.query || 'Demo search')
const errorText = (e: unknown) => e instanceof Error ? e.message : 'An unexpected error occurred.'
const active = (job: Job) => job.status === 'running' || job.status === 'queued'

type Toast = { message: string; kind: 'success' | 'error' }

function Status({ status }: { status: Job['status'] }) {
  const map: Record<Job['status'], string> = { queued: 'Queued', running: 'Running', completed: 'Completed', failed: 'Failed' }
  return <span className={`status status-${status}`}><span className="status-dot" />{map[status]}</span>
}
function Empty({ icon: Icon, title, copy, action }: { icon: LucideIcon; title: string; copy: string; action?: ReactNode }) {
  return <div className="empty"><div className="empty-icon"><Icon size={26} /></div><h3>{title}</h3><p>{copy}</p>{action}</div>
}
function PanelHeading({ title, sub, action }: { title: string; sub?: string; action?: ReactNode }) {
  return <div className="panel-heading"><div><h2>{title}</h2>{sub && <p>{sub}</p>}</div>{action}</div>
}
function Kpi({ icon: Icon, label, value, note, accent }: { icon: LucideIcon; label: string; value: string | number; note: string; accent: string }) {
  return <div className="kpi"><div className="kpi-head"><span>{label}</span><span className={`kpi-icon ${accent}`}><Icon size={18} /></span></div><strong>{value}</strong><span className="kpi-note">{note}</span></div>
}

function App({ user }: { user: User }) {
  const [page, setPage] = useState<Page>('overview')
  const [mobileMenu, setMobileMenu] = useState(false)
  const [health, setHealth] = useState<Health | null>(null)
  const [online, setOnline] = useState(false)
  const [jobsError, setJobsError] = useState<string | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [firstLoad, setFirstLoad] = useState(true)
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState<Toast | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [leads, setLeads] = useState<Lead[]>([])
  const [leadOffset, setLeadOffset] = useState(0)
  const [loadingLeads, setLoadingLeads] = useState(false)
  const [filter, setFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('Roofing contractors')
  const [searchLocation, setSearchLocation] = useState('Houston, TX')
  const [searchCount, setSearchCount] = useState('25')
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const uploadRef = useRef<HTMLInputElement>(null)

  const notify = useCallback((message: string, kind: Toast['kind'] = 'success') => setToast({ message, kind }), [])
  useEffect(() => { if (!toast) return; const id = window.setTimeout(() => setToast(null), 5500); return () => window.clearTimeout(id) }, [toast])

  const refresh = useCallback(async (silent = false) => {
    // A healthy public API does not imply the authenticated jobs request succeeded.
    // Keep the two states separate so a session error is not labeled as a server outage.
    const [healthResult, jobsResult] = await Promise.allSettled([api.health(), api.jobs()])
    const isHealthy = healthResult.status === 'fulfilled'
    setHealth(isHealthy ? healthResult.value : null)
    setOnline(isHealthy)

    if (jobsResult.status === 'fulfilled') {
      setJobsError(null)
      setJobs(jobsResult.value.jobs)
      setSelectedId(prev => jobsResult.value.jobs.some(job => job.id === prev) ? prev : (jobsResult.value.jobs[0]?.id ?? null))
      if (!silent && isHealthy) notify('Your workspace is up to date.')
    } else {
      setJobsError(errorText(jobsResult.reason))
      setJobs([])
      setSelectedId(null)
      setLeads([])
      if (!silent) notify(errorText(jobsResult.reason), 'error')
    }
    if (!silent && !isHealthy && jobsResult.status === 'fulfilled') notify(errorText(healthResult.status === 'rejected' ? healthResult.reason : 'API health check failed.'), 'error')
    setFirstLoad(false)
  }, [notify])

  useEffect(() => { void refresh(true) }, [refresh])
  const runningJobs = jobs.some(active)
  useEffect(() => {
    if (!runningJobs) return
    const interval = window.setInterval(() => { void refresh(true) }, 2500)
    return () => window.clearInterval(interval)
  }, [refresh, runningJobs])

  const selectedJob = jobs.find(j => j.id === selectedId) ?? null
  const selectedStatus = selectedJob?.status
  const selectedFound = selectedJob?.found
  useEffect(() => {
    if (!selectedId) { setLeads([]); return }
    let canceled = false
    setLoadingLeads(true)
    api.leads(selectedId, PAGE_SIZE, leadOffset).then(result => {
      if (!canceled) setLeads(result.leads)
    }).catch(error => {
      if (!canceled) { setLeads([]); notify(errorText(error), 'error') }
    }).finally(() => { if (!canceled) setLoadingLeads(false) })
    return () => { canceled = true }
  }, [selectedId, leadOffset, selectedStatus, selectedFound, notify])

  const chooseJob = (jobId: string, nextPage: Page = 'leads') => {
    setSelectedId(jobId)
    setLeadOffset(0)
    setFilter('')
    setPage(nextPage)
    setMobileMenu(false)
  }
  const goto = (nextPage: Page) => { setPage(nextPage); setMobileMenu(false) }

  const startSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const query = searchQuery.trim()
    const location = searchLocation.trim()
    const amount = Number(searchCount)
    if (query.length < 2 || location.length < 2 || amount < 1 || amount > 50) {
      notify('Enter a business type and location (at least 2 characters each), and 1–50 results.', 'error'); return
    }
    setBusy(true)
    try {
      const job = await api.search(query, location, amount)
      setJobs(prev => [job, ...prev.filter(j => j.id !== job.id)])
      chooseJob(job.id, 'jobs')
      notify('Demo search submitted. Results will appear when the job completes.')
      void refresh(true)
    } catch (error) { notify(errorText(error), 'error') }
    finally { setBusy(false) }
  }
  const startImport = async () => {
    if (!file) { notify('Select a CSV file to import.', 'error'); return }
    if (!file.name.toLowerCase().endsWith('.csv')) { notify('Please select a .csv file.', 'error'); return }
    if (file.size > 2 * 1024 * 1024) { notify('File exceeds the 2 MB upload limit.', 'error'); return }
    setBusy(true)
    try {
      const job = await api.importCsv(file)
      setJobs(prev => [job, ...prev.filter(j => j.id !== job.id)])
      setFile(null)
      if (uploadRef.current) uploadRef.current.value = ''
      chooseJob(job.id, 'jobs')
      notify('CSV accepted and queued for cleaning and import.')
      void refresh(true)
    } catch (error) { notify(errorText(error), 'error') }
    finally { setBusy(false) }
  }
  const exportSelected = async () => {
    if (!selectedJob || selectedJob.status !== 'completed') return
    setBusy(true)
    try { const count = await downloadJobCsv(selectedJob.id, selectedJob.kind); notify(`Exported ${count.toLocaleString()} records.`) }
    catch (error) { notify(errorText(error), 'error') }
    finally { setBusy(false) }
  }
  const stats = useMemo(() => ({
    total: jobs.reduce((sum, job) => sum + job.found, 0),
    completed: jobs.filter(job => job.status === 'completed').length,
    running: jobs.filter(active).length,
    imports: jobs.filter(job => job.kind === 'csv-import').length,
  }), [jobs])
  const filteredLeads = leads.filter(lead => Object.values(lead).some(v => String(v ?? '').toLowerCase().includes(filter.trim().toLowerCase())))
  const sectionTitle: Record<Page, string> = { overview: 'Overview', search: 'Lead search', leads: 'Lead explorer', jobs: 'Job history', import: 'Import leads', settings: 'Settings' }
  const caption: Record<Page, string> = { overview: 'Your workspace at a glance', search: 'Configure and run a safe demo search', leads: 'Review, filter, and export your records', jobs: 'Monitor your processing activity', import: 'Upload data you are authorized to use', settings: 'Connection details and workspace capabilities' }

  return <div className="app-shell">
    {mobileMenu && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setMobileMenu(false)} />}
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <button className="brand" onClick={() => goto('overview')} aria-label="LeadScraper overview"><span className="brand-mark"><Radar size={23} /></span><span className="brand-text">lead<span>scraper</span><small>WORKSPACE</small></span></button>
      <div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Main navigation" className="side-nav">
        {primaryNav.map(item => <button key={item.page} className={`nav-item ${page === item.page ? 'selected' : ''}`} onClick={() => goto(item.page)}><item.icon size={19} strokeWidth={1.9} /><span>{item.label}</span>{item.page === 'jobs' && stats.running > 0 && <span className="nav-count">{stats.running}</span>}</button>)}
      </nav>
      <div className="sidebar-label second-label">SYSTEM</div>
      <nav className="side-nav" aria-label="System navigation"><button className={`nav-item ${page === 'settings' ? 'selected' : ''}`} onClick={() => goto('settings')}><Settings2 size={19} />Settings</button></nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-info"><span className="safe-indicator"><ShieldAlert size={16} /> PRIVATE WORKSPACE</span><p>Signed in with Supabase. Your jobs and lead records belong to your account.</p></div>
      <div className="sidebar-footer"><span className="avatar">{(user.email || "U").slice(0, 1).toUpperCase()}</span><span><strong title={user.email}>{user.email || "Account"}</strong><small>Protected account</small></span><button className="signout-btn" type="button" title="Sign out" aria-label="Sign out" onClick={() => void supabase?.auth.signOut()}><LogOut size={18}/></button></div>
    </aside>

    <div className="main-shell">
      <header className="topbar">
        <div className="topbar-left"><button className="icon-btn mobile-nav" aria-label="Open navigation" onClick={() => setMobileMenu(true)}><Menu size={22} /></button><span className="crumb">Workspace</span><ChevronRight size={15} className="crumb-sep" /><strong>{sectionTitle[page]}</strong></div>
        <div className="topbar-right"><span className={`connection ${online ? 'online' : 'offline'}`}><span className="connection-dot" />{online ? 'API connected' : 'API offline'}</span><button className="icon-btn" aria-label="Refresh API data" title="Refresh API data" onClick={() => void refresh(false)}><RefreshCw size={18} /></button><button className="account-logout" onClick={() => void supabase?.auth.signOut()} title="Sign out"><LogOut size={16}/> Sign out</button></div>
      </header>

      <main className="content">
        <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-mark" /> LEAD INTELLIGENCE / WORKSPACE</div><h1>{sectionTitle[page]}</h1><p>{caption[page]}</p></div><div className="heading-tools"><button className="btn btn-secondary" onClick={() => void refresh(false)}><RefreshCw size={16} /> Refresh</button>{page !== 'search' && <button className="btn btn-primary" onClick={() => goto('search')}><Plus size={17} /> New search</button>}</div></div>

        {!online && <div role="alert" className="offline-banner"><AlertCircle size={19} /><div><strong>API connection unavailable.</strong> {API_BASE.includes('127.0.0.1') ? 'Start your local FastAPI server, then retry.' : 'Your hosted backend may be waking up or temporarily unavailable. Check Render service status and the API URL in Settings, then click Refresh.'}</div></div>}
        {online && jobsError && <div role="alert" className="offline-banner"><AlertCircle size={19} /><div><strong>The API is online, but your jobs could not be loaded.</strong> {jobsError} Check your sign-in session and retry. If the problem continues, inspect Render logs.</div></div>}
        {online && <div className="demo-strip"><Sparkles size={15} /><span>Demo search mode — generated businesses are fictional. Import only CSV data you are authorized to store and export.</span></div>}

        {page === 'overview' && <>
          <section className="hero"><div className="hero-content"><div className="hero-pill"><Zap size={14} /> YOUR LEAD WORKFLOW, SIMPLIFIED</div><h2>Discover. Organize.<br/><span>Move faster.</span></h2><p>A focused command center for running searches, processing imported contacts, and managing your lead data.</p><div className="hero-actions"><button className="btn btn-primary hero-button" onClick={() => goto('search')}><Radar size={18} /> Start a search <ArrowUpRight size={16} /></button><button className="btn btn-ghost-light" onClick={() => goto('import')}><FileUp size={17} /> Import CSV</button></div></div><div className="hero-graphic" aria-hidden="true"><div className="radar-rings"><div className="radar-line"/><div className="blip blip-one"/><div className="blip blip-two"/><div className="blip blip-three"/><div className="radar-center"><Radar size={44} strokeWidth={1.3} /></div></div><div className="floating-chip chip-one"><CheckCircle2 size={15}/> Job complete</div><div className="floating-chip chip-two"><Database size={15}/> Leads ready</div></div></section>
          <section className="kpi-grid" aria-label="Summary statistics"><Kpi icon={Database} label="Processed records" value={stats.total.toLocaleString()} note="In the 50 most recent jobs" accent="indigo" /><Kpi icon={CheckCircle2} label="Completed jobs" value={stats.completed} note="Processed successfully" accent="mint" /><Kpi icon={Activity} label="Active jobs" value={stats.running} note="Queued or processing" accent="amber" /><Kpi icon={FileSpreadsheet} label="CSV imports" value={stats.imports} note="Uploaded data batches" accent="blue" /></section>
          <div className="overview-grid"><section className="panel"><PanelHeading title="Recent activity" sub="Your latest searches and imports" action={<button className="text-link" onClick={() => goto('jobs')}>View all <ArrowRight size={15}/></button>}/>{firstLoad ? <div className="loading-line"><LoaderCircle className="spin" size={20}/> Loading jobs…</div> : jobs.length ? <div className="activity-list">{jobs.slice(0, 5).map(job => <button key={job.id} className="activity-item" onClick={() => chooseJob(job.id)}><span className={`activity-symbol ${job.kind === 'csv-import' ? 'import-symbol' : ''}`}>{job.kind === 'csv-import' ? <FileUp size={19} /> : <Radar size={19} />}</span><span className="activity-description"><strong>{niceName(job)}</strong><small>{job.kind === 'csv-import' ? 'Import and clean data' : (job.location || 'Demo search')} · {niceDate(job.created_at)}</small></span><Status status={job.status}/><ChevronRight size={17} className="muted" /></button>)}</div> : <Empty icon={Clock3} title="No activity yet" copy="Start a demo search or import a CSV to see your work here." action={<button className="btn btn-primary" onClick={() => goto('search')}>Create first job <ArrowRight size={15}/></button>} />}</section><section className="panel quick-panel"><PanelHeading title="Quick actions" sub="Pick up right where you left off"/><button className="quick-action" onClick={() => goto('search')}><span className="quick-icon violet"><Radar size={20}/></span><span><strong>New demo search</strong><small>Find synthetic businesses by category</small></span><ArrowUpRight size={17}/></button><button className="quick-action" onClick={() => goto('import')}><span className="quick-icon cyan"><UploadCloud size={20}/></span><span><strong>Upload a CSV file</strong><small>Clean and deduplicate contacts</small></span><ArrowUpRight size={17}/></button><button className="quick-action" onClick={() => goto('leads')}><span className="quick-icon green"><Users size={20}/></span><span><strong>Explore lead records</strong><small>Review your processed data</small></span><ArrowUpRight size={17}/></button><div className="small-note"><CircleHelp size={16}/> Your records are stored in your account’s configured database. Demo searches generate fictional leads.</div></section></div>
        </>}

        {page === 'search' && <div className="feature-layout"><section className="panel form-panel"><PanelHeading title="Create a search" sub="Configure your business discovery request"/><form onSubmit={startSearch} className="search-form"><label htmlFor="industry">Business type <span className="required">*</span></label><div className="field-icon"><Search size={18}/><input id="industry" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} minLength={2} maxLength={120} placeholder="e.g. Roofing contractors" required /></div><span className="field-hint">What type of businesses are you looking for?</span><label htmlFor="location">Target location <span className="required">*</span></label><div className="field-icon"><Globe2 size={18}/><input id="location" value={searchLocation} onChange={e => setSearchLocation(e.target.value)} minLength={2} maxLength={120} placeholder="e.g. Houston, TX" required /></div><span className="field-hint">City, region, or geographic market</span><label htmlFor="results">Maximum results</label><div className="field-icon"><ListChecks size={18}/><select id="results" value={searchCount} onChange={e => setSearchCount(e.target.value)}>{[10,25,50].map(n => <option key={n} value={n}>{n} leads</option>)}</select><ChevronDown className="select-chevron" size={18}/></div><div className="info-callout"><Sparkles size={19}/><div><strong>Demo data source</strong><p>This phase generates fictional leads to validate the workflow. Live licensed data providers can be integrated later.</p></div></div><button className="btn btn-primary submit-btn" type="submit" disabled={busy || !online}>{busy ? <LoaderCircle size={19} className="spin"/> : <Play size={18} fill="currentColor"/>}{busy ? 'Submitting…' : 'Run demo search'} <ArrowRight size={18}/></button></form></section><aside className="panel help-panel"><div className="help-emblem"><Terminal size={28}/></div><h3>How it works</h3><p>Every request runs through your Python backend and is tracked as an independent job.</p><div className="steps-line"><div><span>01</span><strong>Submit criteria</strong><small>Choose a category and location</small></div><div><span>02</span><strong>Process leads</strong><small>Backend validates and saves results</small></div><div><span>03</span><strong>Review and export</strong><small>Use your lead explorer to see records</small></div></div><div className="help-footer"><ShieldAlert size={18}/><p>Production search APIs require their own storage and export permissions.</p></div></aside></div>}

        {page === 'import' && <div className="feature-layout"><section className="panel form-panel"><PanelHeading title="Import your leads" sub="Bring existing, authorized lead data into your workspace"/><input ref={uploadRef} className="visually-hidden" id="csv-input" type="file" accept=".csv,text/csv" onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] ?? null)}/><div role="button" tabIndex={0} aria-label="Choose CSV file" className={`dropzone ${dragging ? 'dragging' : ''}`} onClick={() => uploadRef.current?.click()} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); uploadRef.current?.click() } }} onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]) }}><div className="upload-image"><UploadCloud size={36}/></div><h3>{file ? file.name : 'Drag and drop your CSV here'}</h3><p>{file ? `${(file.size / 1024).toFixed(1)} KB · Ready to import` : 'or click anywhere here to browse your files'}</p><span className="file-tag">CSV ONLY · MAX 2 MB · UP TO 2,000 ROWS</span></div>{file && <button className="remove-file" onClick={() => { setFile(null); if(uploadRef.current) uploadRef.current.value = '' }}><X size={15}/> Remove selected file</button>}<div className="info-callout"><ShieldAlert size={19}/><div><strong>Use permitted data only</strong><p>Only upload CSVs you own or are licensed to store and export. Do not upload restricted Google Places listings.</p></div></div><button className="btn btn-primary submit-btn" onClick={() => void startImport()} disabled={!file || busy || !online}>{busy ? <LoaderCircle size={19} className="spin"/> : <FileUp size={19}/>} {busy ? 'Uploading…' : 'Import and clean CSV'}<ArrowRight size={18}/></button></section><aside className="panel help-panel"><div className="help-emblem"><FileSpreadsheet size={28}/></div><h3>Supported columns</h3><p>Your CSV can include any of these recognizable field names:</p><div className="columns-list">{['Name / Business Name','Address / Street Address','Phone / Phone Number','Email / Email Address','Website / URL'].map(field=><span key={field}><Check size={16}/>{field}</span>)}</div><p className="secondary-copy">The Python backend normalizes common US phone numbers and removes duplicate rows. UTF-8 CSV files are supported.</p></aside></div>}

        {page === 'jobs' && <section className="panel full-panel"><PanelHeading title="Processing history" sub={`${jobs.length} recent jobs · Auto-refreshes while jobs are active`} action={<button className="btn btn-small btn-secondary" onClick={() => void refresh(false)}><RefreshCw size={15}/> Refresh</button>}/>{!jobs.length ? <Empty icon={ListChecks} title="No jobs found" copy="Create a demo search or import a CSV to get started." action={<button className="btn btn-primary" onClick={() => goto('search')}>New search</button>}/> : <div className="table-scroll"><table className="data-table job-table"><thead><tr><th>JOB</th><th>TYPE</th><th>CREATED</th><th>RECORDS</th><th>STATUS</th><th aria-label="Actions" /></tr></thead><tbody>{jobs.map(job => <tr key={job.id}><td><strong>{niceName(job)}</strong><small>{job.location || `Job #${job.id.slice(0,8)}`}</small></td><td>{job.kind === 'csv-import' ? 'CSV import' : 'Demo search'}</td><td>{niceDate(job.created_at)}</td><td>{job.found.toLocaleString()}{job.requested ? ` / ${job.requested}` : ''}</td><td><Status status={job.status}/>{job.status === 'failed' && job.message && <small className="fail-note">{job.message}</small>}</td><td><button className="row-link" onClick={() => chooseJob(job.id)}>View leads <ArrowUpRight size={15}/></button></td></tr>)}</tbody></table></div>}</section>}

        {page === 'leads' && <section className="panel full-panel"><PanelHeading title="Lead explorer" sub="Inspect a completed search or CSV import" action={<button className="btn btn-secondary btn-small" disabled={!selectedJob || selectedJob.status !== 'completed' || busy || !online} onClick={() => void exportSelected()}><ArrowDownToLine size={16}/>{busy ? 'Exporting…' : 'Export all to CSV'}</button>}/>{jobs.length ? <><div className="explorer-tools"><div className="job-picker-wrap"><label htmlFor="job-picker">DATA SOURCE</label><div className="job-picker"><Database size={17}/><select id="job-picker" value={selectedId || ''} onChange={e => chooseJob(e.target.value)}>{jobs.map(job => <option key={job.id} value={job.id}>{niceName(job)} — {niceDate(job.created_at)}</option>)}</select><ChevronDown size={16}/></div></div><div className="lead-filter"><Filter size={17}/><input aria-label="Filter current page" placeholder="Filter this page…" value={filter} onChange={e => setFilter(e.target.value)} /></div></div>{selectedJob && <div className="results-bar"><div><Status status={selectedJob.status}/><span>{selectedJob.found.toLocaleString()} total records for selected job</span></div><span>Showing page {Math.floor(leadOffset / PAGE_SIZE) + 1}</span></div>}{loadingLeads ? <div className="loading-line"><LoaderCircle className="spin" size={20}/> Loading lead records…</div> : filteredLeads.length ? <div className="table-scroll"><table className="data-table leads-table"><thead><tr><th>BUSINESS</th><th>PHONE</th><th>EMAIL</th><th>LOCATION</th><th>SOURCE</th></tr></thead><tbody>{filteredLeads.map(lead => <tr key={lead.id}><td><div className="company-cell"><span className="company-initial">{(lead.name || '?').charAt(0).toUpperCase()}</span><span><strong>{lead.name || 'Unnamed business'}</strong>{lead.website && <a href={lead.website} target="_blank" rel="noopener noreferrer" title={lead.website}>Website <ArrowUpRight size={12}/></a>}</span></div></td><td>{lead.phone || <span className="no-data">—</span>}</td><td>{lead.email ? <a className="table-email" href={`mailto:${lead.email}`}>{lead.email}</a> : <span className="no-data">—</span>}</td><td className="truncate-cell" title={lead.address || ''}>{lead.address || '—'}</td><td><span className={`source-tag ${lead.source === 'synthetic-demo' ? 'demo' : ''}`}>{lead.source === 'synthetic-demo' ? 'DEMO' : 'CSV'}</span></td></tr>)}</tbody></table></div> : <Empty icon={Search} title={filter ? 'No matching records' : 'No leads to display'} copy={filter ? 'Try a different filter; it searches only the current page of results.' : selectedJob?.status === 'completed' ? 'This job finished without records.' : 'This job is still processing, or it has no results yet.'}/>}{selectedJob && <div className="table-footer"><span>{leadOffset + (leads.length ? 1 : 0)}–{leadOffset + leads.length} of {selectedJob.found.toLocaleString()} · Filters apply to current page</span><div><button className="btn btn-small btn-secondary" disabled={leadOffset === 0 || loadingLeads} onClick={() => { setLeadOffset(o => Math.max(0, o - PAGE_SIZE)); setFilter('') }}><ArrowLeft size={15}/> Previous</button><button className="btn btn-small btn-secondary" disabled={loadingLeads || leads.length < PAGE_SIZE || leadOffset + leads.length >= selectedJob.found} onClick={() => { setLeadOffset(o => o + PAGE_SIZE); setFilter('') }}>Next <ArrowRight size={15}/></button></div></div>}</> : <Empty icon={Database} title="Your lead explorer is empty" copy="Create your first job to populate this workspace." action={<button className="btn btn-primary" onClick={() => goto('search')}>Create a job</button>}/>}</section>}

        {page === 'settings' && <div className="settings-grid"><section className="panel settings-panel"><PanelHeading title="Backend connection" sub="Live connection and service details"/><div className="setting-item"><span className="setting-icon"><Server size={19}/></span><div><strong>API base URL</strong><p><code>{API_BASE}</code></p></div><span className={`setting-state ${online ? 'good' : 'bad'}`}>{online ? 'Connected' : 'Offline'}</span></div><div className="setting-item"><span className="setting-icon"><Database size={19}/></span><div><strong>Storage</strong><p>{health?.storage || "Database status unavailable"}</p></div></div><div className="setting-item"><span className="setting-icon"><ShieldAlert size={19}/></span><div><strong>Authentication</strong><p>{health?.authentication || 'Supabase JWT authentication enabled'}</p></div></div><div className="setting-item"><span className="setting-icon"><HardDrive size={19}/></span><div><strong>Job processing</strong><p>{health?.processing || 'Status unavailable'}</p></div></div><button className="btn btn-secondary" onClick={() => void refresh(false)}><RefreshCw size={17}/> Recheck connection</button></section><section className="panel settings-panel"><PanelHeading title="Workspace capabilities" sub="Current services and operating limits"/><div className="guard-list"><p><CheckCircle2 size={19}/> Supabase sign-in protects private workspace requests.</p><p><CheckCircle2 size={19}/> The API verifies access tokens and checks record ownership.</p><p><AlertCircle size={19}/> Searches currently generate fictional demo leads, not live business records.</p><p><AlertCircle size={19}/> Imported CSVs must come from authorized data sources.</p><p><AlertCircle size={19}/> Free-hosting jobs may be interrupted when the server sleeps or restarts. Retry failed jobs.</p></div><div className="settings-next"><strong>Future enhancement</strong><p>Integrate a business-data provider that permits your intended searches, storage, and exports. Add durable workers when usage justifies paid hosting.</p></div></section></div>}

        <footer className="content-footer"><span><span className="mini-logo"><Radar size={15}/></span> LeadScraper <span className="footer-muted">/ Built for focused prospecting workflows</span></span><span>Cloud workspace · Demo searches + CSV import</span></footer>
      </main>
    </div>
    {toast && <div role="alert" className={`toast toast-${toast.kind}`}>{toast.kind === 'error' ? <AlertCircle size={19}/> : <CheckCircle2 size={19}/>}<span>{toast.message}</span><button aria-label="Dismiss notification" onClick={() => setToast(null)}><X size={17}/></button></div>}
  </div>
}

export default App
