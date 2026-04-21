import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchStudents, fetchStats, photoUrl } from '../api'

const domainColors = {
  backend: '#6366f1', machine_learning: '#f59e0b', vlsi_design: '#10b981',
  data_science: '#3b82f6', nlp: '#8b5cf6', computer_vision: '#ec4899',
  embedded_systems: '#14b8a6', devops: '#f97316', deep_learning: '#a855f7',
  cloud: '#06b6d4', general: '#94a3b8', webdev: '#ef4444',
  digital_electronics: '#059669', analog_circuits: '#34d399',
  frontend: '#fb923c',
}

export default function Dashboard() {
  const [students, setStudents] = useState([])
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('')
  const [domainFilter, setDomainFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([fetchStudents(), fetchStats()])
      .then(([s, st]) => { setStudents(s); setStats(st) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const domains = [...new Set(students.map(s => s.primary_domain || 'general'))]

  const filtered = students.filter(s => {
    const matchName = s.name.toLowerCase().includes(filter.toLowerCase())
    const matchDomain = !domainFilter || (s.primary_domain || 'general') === domainFilter
    return matchName && matchDomain
  })

  if (loading) return <div><div className="spinner" /><p className="loading-text">Loading students...</p></div>

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Student Dashboard</h1>
        <p className="page-subtitle">{students.length} students indexed · {stats?.total_companies || 0} companies · {stats?.index_vectors || 0} vectors</p>
      </div>

      {stats && (
        <div className="stats-row">
          <div className="stat-card"><div className="stat-value">{stats.total_students}</div><div className="stat-label">Total Students</div></div>
          <div className="stat-card"><div className="stat-value">{stats.total_with_work}</div><div className="stat-label">With Work Exp</div></div>
          <div className="stat-card"><div className="stat-value">{stats.total_with_projects}</div><div className="stat-label">With Projects</div></div>
          <div className="stat-card"><div className="stat-value">{stats.total_companies}</div><div className="stat-label">Companies</div></div>
          <div className="stat-card"><div className="stat-value">{stats.index_vectors}</div><div className="stat-label">FAISS Vectors</div></div>
        </div>
      )}

      <div className="search-container">
        <span className="search-icon">🔍</span>
        <input className="search-input" placeholder="Filter students by name..." value={filter} onChange={e => setFilter(e.target.value)} />
      </div>

      <div className="filter-row">
        <button className={`filter-chip ${!domainFilter ? 'active' : ''}`} onClick={() => setDomainFilter('')}>All</button>
        {domains.sort().map(d => (
          <button key={d} className={`filter-chip ${domainFilter === d ? 'active' : ''}`} onClick={() => setDomainFilter(d)}
            style={domainFilter === d ? { borderColor: domainColors[d], color: domainColors[d] } : {}}>
            {d.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <div className="students-grid">
        {filtered.map(s => (
          <div key={s.name} className="student-card" onClick={() => navigate(`/student/${encodeURIComponent(s.name)}`)}>
            <div className="card-top">
              {s.photo_url
                ? <img className="card-avatar" src={photoUrl(s.photo_url)} alt={s.name} />
                : <div className="card-avatar-placeholder">{s.name.charAt(0)}</div>
              }
              <div className="card-info">
                <div className="card-name">{s.name}</div>
                <div className="card-branch">{s.branch || 'N/A'} {s.cgpa ? `· ${s.cgpa} CGPA` : ''}</div>
              </div>
            </div>
            <div className="card-body">
              <span className="card-domain" style={{ borderColor: domainColors[s.primary_domain] + '40', color: domainColors[s.primary_domain] || 'var(--accent)' }}>
                {(s.primary_domain || 'general').replace(/_/g, ' ')}
              </span>
              <div className="card-scores">
                {Object.entries(s.top_scores || {}).slice(0, 4).map(([k, v]) => (
                  <span key={k} className="score-pill">
                    <span className="score-pill-label">{k.replace(/_/g, ' ')}</span>
                    <span className="score-pill-value">{v}</span>
                  </span>
                ))}
              </div>
              {s.companies?.[0] && (
                <div className="card-company">💼 <span>{s.companies[0].role}</span> at {s.companies[0].company}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
