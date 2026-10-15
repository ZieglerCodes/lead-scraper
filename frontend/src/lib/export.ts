import { api, type Lead } from './api'

const COLUMNS: (keyof Pick<Lead, 'name' | 'address' | 'phone' | 'email' | 'website' | 'source'>)[] = ['name', 'address', 'phone', 'email', 'website', 'source']

// Escape Excel formula injection; these cells may contain untrusted, imported text.
function csvCell(value: string | null | undefined): string {
  let safe = value ?? ''
  if (/^[\s\uFEFF\u200B]*[=+@\-\t\r]/.test(safe)) safe = `'${safe}`
  return `"${safe.replace(/"/g, '""')}"`
}

export async function downloadJobCsv(jobId: string, kind: string): Promise<number> {
  const all: Lead[] = []
  let offset = 0
  const limit = 500
  for (;;) {
    const response = await api.leads(jobId, limit, offset)
    all.push(...response.leads)
    if (response.leads.length < limit) break
    offset += response.leads.length
    if (offset >= 5000) throw new Error('CSV export exceeded the local development limit of 5,000 rows.')
  }
  const lines = [COLUMNS.map(csvCell).join(','), ...all.map(lead => COLUMNS.map(key => csvCell(lead[key])).join(','))]
  const blob = new Blob(['\uFEFF', lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `lead-scraper-${kind}-${jobId.slice(0, 8)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  return all.length
}
