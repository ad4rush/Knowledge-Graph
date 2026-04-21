import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchStudents, photoUrl } from '../api'

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await searchStudents(query, 15, false)
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">AI-Powered Search</h1>
        <p className="page-subtitle">Find the best candidates using natural language queries</p>
      </div>

      <form onSubmit={handleSearch} style={{ marginBottom: 32 }}>
        <div className="search-container">
          <span className="search-icon">🔍</span>
          <input
            className="search-input"
            placeholder='Try: "who knows machine learning the best" or "frontend developer with React"'
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? '⏳ Searching...' : '🚀 Search'}
        </button>
      </form>

      {loading && (
        <div>
          <div className="spinner" />
          <p className="loading-text">Embedding query & searching FAISS index...<br />Then re-ranking with Gemini AI...</p>
        </div>
      )}

      {error && <div style={{ color: 'var(--danger)', padding: 20, background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--danger)' }}>{error}</div>}

      {results && !loading && (
        <div className="search-results-layout">
          <div className="search-results-list">
            <h3 style={{ color: 'var(--text-bright)', marginBottom: 8 }}>
              Top {results.candidates.length} Matches
            </h3>
            {results.candidates.map((c, i) => (
              <div key={i} className="search-result-card" onClick={() => navigate(`/student/${encodeURIComponent(c.name)}`)}>
                {c.photo_url
                  ? <img className="result-photo" src={photoUrl(c.photo_url)} alt={c.name} />
                  : <div className="result-photo-placeholder">{c.name?.charAt(0)}</div>
                }
                <div className="result-info">
                  <div className="result-name">#{i + 1} {c.name}</div>
                  <div className="result-meta">
                    {c.branch && <span>{c.branch}</span>}
                    {c.primary_domain && <span> · {c.primary_domain.replace(/_/g, ' ')}</span>}
                    {c.cgpa && <span> · {c.cgpa} CGPA</span>}
                  </div>
                  <div className="result-score">
                    Vector Similarity: {(c.score * 100).toFixed(1)}%
                    {c.top_domains && <span style={{ marginLeft: 8, color: 'var(--text-dim)' }}>Domains: {c.top_domains.replace(/;/g, ', ')}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {results.ai_analysis && (
            <div className="ai-panel">
              <div className="ai-panel-title">🤖 AI Re-Ranking & Reasoning</div>
              <div className="ai-panel-content">{results.ai_analysis}</div>
            </div>
          )}
        </div>
      )}

      {!results && !loading && (
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: '4rem', marginBottom: 16 }}>🧠</div>
          <h2 style={{ color: 'var(--text-bright)', fontWeight: 700 }}>Semantic Resume Search</h2>
          <p style={{ color: 'var(--text-dim)', maxWidth: 500, margin: '12px auto', lineHeight: 1.6 }}>
            Enter a natural language query above. The system will embed your query, search the FAISS vector database,
            then re-rank results using Gemini AI with detailed reasoning.
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap', marginTop: 20 }}>
            {['machine learning expert', 'VLSI design engineer', 'full-stack developer', 'backend with Kubernetes'].map(q => (
              <button key={q} className="filter-chip" onClick={() => { setQuery(q) }}>{q}</button>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
