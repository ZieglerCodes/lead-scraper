import { supabase } from './supabase'

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed'
export type JobKind = 'search-demo' | 'csv-import'
export type Job = {
  id: string
  owner_id: string
  kind: JobKind
  status: JobStatus
  query: string | null
  location: string | null
  requested: number
  found: number
  message: string | null
  created_at: string
  updated_at: string
}
export type Lead = {
  id: string
  name: string | null
  address: string | null
  phone: string | null
  email: string | null
  website: string | null
  source: string
  created_at: string
}
export type Health = { status: string; phase: number; authentication: string; storage?: string; processing?: string }
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); this.name = 'ApiError' }
}

async function request<T>(path: string, options: RequestInit = {}, authenticated = true): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 20000)
  try {
    const headers = new Headers(options.headers)
    if (authenticated) {
      if (!supabase) throw new ApiError('Supabase authentication is not configured.', 401)
      // Supabase refreshes expired sessions as needed; API independently validates JWT.
      const { data: { session }, error } = await supabase.auth.getSession()
      if (error || !session?.access_token) throw new ApiError('Session expired. Please sign in again.', 401)
      headers.set('Authorization', `Bearer ${session.access_token}`)
    }
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal })
    let data: unknown
    try { data = await response.json() } catch { data = null }
    if (!response.ok) {
      const detail = data && typeof data === 'object' && 'detail' in data ? (data as { detail: unknown }).detail : null
      const reason = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: { msg?: string }) => e.msg || 'Invalid input').join('; ') : `Request failed (HTTP ${response.status})`
      throw new ApiError(reason, response.status)
    }
    return data as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError('The API request timed out. Check the backend server.')
    throw new ApiError(`Cannot reach the API at ${API_BASE}. Check your backend URL, CORS configuration, and deployment status.`)
  } finally { window.clearTimeout(timeout) }
}

export const api = {
  health: () => request<Health>('/api/health', {}, false),
  me: () => request<{ id: string }>('/api/me'),
  jobs: () => request<{ jobs: Job[] }>('/api/jobs'),
  job: (id: string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  leads: (id: string, limit = 100, offset = 0) => request<{ job_id: string; status: JobStatus; leads: Lead[] }>(`/api/jobs/${encodeURIComponent(id)}/leads?limit=${limit}&offset=${offset}`),
  search: (query: string, location: string, maxResults: number) => request<Job>('/api/jobs/search', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, location, max_results: maxResults, source: 'demo' }),
  }),
  importCsv: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<Job>('/api/jobs/import', { method: 'POST', body })
  },
}
