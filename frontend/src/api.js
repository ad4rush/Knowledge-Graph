const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function fetchStudents() {
  const res = await fetch(`${BASE}/api/students`)
  if (!res.ok) throw new Error('Failed to fetch students')
  return res.json()
}

export async function fetchStudent(name) {
  const res = await fetch(`${BASE}/api/students/${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error('Student not found')
  return res.json()
}

export async function fetchStats() {
  const res = await fetch(`${BASE}/api/stats`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export async function searchStudents(query, top = 5, skipLlm = false) {
  const res = await fetch(`${BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top, skip_llm: skipLlm }),
  })
  if (!res.ok) throw new Error('Search failed')
  return res.json()
}

export async function uploadResumes(files) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  const res = await fetch(`${BASE}/api/upload`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

export async function fetchGraphData() {
  const res = await fetch(`${BASE}/api/graph`)
  if (!res.ok) throw new Error('Failed to fetch graph')
  return res.json()
}

export function photoUrl(path) {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `${BASE}${path}`
}
