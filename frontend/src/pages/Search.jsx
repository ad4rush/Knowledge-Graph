import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchStudents, photoUrl } from '../api'

/**
 * Lightweight markdown → HTML converter for AI analysis text.
 * Handles: **bold**, *italic*, headers (#-###), lists, and line breaks.
 */
function formatMarkdown(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>')

  // Bold and italic (handling both ** and __)
  html = html.replace(/(\*\*\*|___)(.+?)\1/g, '<strong><em>$2</em></strong>')
  html = html.replace(/(\*\*|__)(.+?)\1/g, '<strong>$2</strong>')
  html = html.replace(/(\*|_)(.+?)\1/g, '<em>$2</em>')

  // Horizontal rules
  html = html.replace(/^---+$/gm, '<hr/>')

  // Lists (Bullet and Numbered)
  // First, convert them to <li>
  html = html.replace(/^[\s]*[-•*]\s+(.+)$/gm, '<li>$1</li>')
  html = html.replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>')
  
  // Wrap groups of <li> in <ul> (more robustly)
  html = html.replace(/(<li>(?:.|\n)*?<\/li>)/g, '<ul>$1</ul>')
  // Cleanup nested <ul> from the above greedy match
  html = html.replace(/<\/ul>\s*<ul>/g, '')

  // Paragraphs and Line breaks
  html = html.replace(/\n\n/g, '</p><p>')
  html = html.replace(/\n/g, '<br/>')

  return `<div class="md-content"><p>${html}</p></div>`
}

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
      const data = await searchStudents(query, 5, false)
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
          <p className="loading-text">Embedding query &amp; searching FAISS index...<br />Then re-ranking with Amazon Nova AI...</p>
        </div>
      )}

      {error && <div style={{ color: 'var(--danger)', padding: 20, background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--danger)' }}>{error}</div>}

      {results && !loading && (
        <div className="search-results-layout">
          <div className="search-results-list">
            <h3 style={{ color: 'var(--text-bright)', marginBottom: 8 }}>
              {results.candidates.length} Matches
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
              <div className="ai-panel-content" dangerouslySetInnerHTML={{ __html: formatMarkdown(results.ai_analysis) }} />
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
            then re-rank results using Amazon Nova AI with detailed reasoning.
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
