import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchStudent, photoUrl } from '../api'

const SKILL_CATS = [
  'webdev','frontend','backend','mobile_dev','app_dev','cloud','devops',
  'data_science','machine_learning','deep_learning','reinforcement_learning',
  'computer_vision','nlp','cybersecurity_cryptography','blockchain_web3',
  'bioinformatics','ar_vr','robotics_automation','big_data',
  'digital_electronics','analog_circuits','vlsi_design','embedded_systems',
  'signal_processing','control_systems','iot','communication_systems',
  'power_systems_power_electronics','quantum_computing','digital_twins_simulation_tools'
]

export default function Profile() {
  const { name } = useParams()
  const [student, setStudent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetchStudent(name)
      .then(setStudent)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [name])

  if (loading) return <div><div className="spinner" /><p className="loading-text">Loading profile...</p></div>
  if (error) return <div style={{ textAlign: 'center', padding: 40 }}><h2 style={{ color: 'var(--danger)' }}>Error</h2><p>{error}</p><Link to="/" className="btn btn-ghost" style={{ marginTop: 16 }}>← Back</Link></div>
  if (!student) return null

  const s = student
  const allScores = Object.entries(s.all_scores || {}).sort((a, b) => b[1] - a[1])
  const topScores = allScores.filter(([, v]) => v > 0)

  return (
    <>
      <Link to="/" style={{ color: 'var(--text-dim)', fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 16 }}>← Back to Dashboard</Link>

      <div className="profile-layout">
        {/* LEFT PANEL */}
        <div className="profile-left">
          {s.photo_url
            ? <img className="profile-avatar" src={photoUrl(s.photo_url)} alt={s.name} />
            : <div className="profile-avatar-placeholder">{s.name.charAt(0)}</div>
          }
          <div className="profile-name">{s.name}</div>
          <div className="profile-domain">{(s.primary_domain || 'general').replace(/_/g, ' ')}</div>

          <div className="profile-links">
            {s.linkedin_url && <a href={s.linkedin_url.startsWith('http') ? s.linkedin_url : `https://${s.linkedin_url}`} target="_blank" rel="noreferrer" className="profile-link-btn">🔗 LinkedIn</a>}
            {s.github_url && <a href={s.github_url.startsWith('http') ? s.github_url : `https://${s.github_url}`} target="_blank" rel="noreferrer" className="profile-link-btn">💻 GitHub</a>}
          </div>

          <div className="profile-meta">
            {[
              ['Branch', s.branch],
              ['College', s.college],
              ['CGPA', s.cgpa],
              ['Batch', s.batch],
              ['Email', s.email],
              ['Top Domains', s.top_3_domains?.replace(/;/g, ', ')],
            ].filter(([, v]) => v).map(([label, value]) => (
              <div className="profile-meta-row" key={label}>
                <span className="profile-meta-label">{label}</span>
                <span className="profile-meta-value">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER */}
        <div className="profile-center">
          {/* Work Experience */}
          {s.companies?.length > 0 && (
            <div className="section-card">
              <div className="section-title"><span className="icon">💼</span> Work Experience</div>
              {s.companies.map((w, i) => (
                <div className="timeline-item" key={i}>
                  <div className="timeline-dot" />
                  <div className="timeline-title">{w.role || 'Employee'}</div>
                  <div className="timeline-subtitle">{w.company}</div>
                  {w.duration && <div className="timeline-duration">{w.duration}</div>}
                  {w.description && <div className="timeline-desc">{w.description}</div>}
                  {w.tools && <div className="timeline-tools">{w.tools.split(';').map(t => <span key={t} className="badge">{t.trim()}</span>)}</div>}
                </div>
              ))}
            </div>
          )}

          {/* Projects */}
          {s.projects?.length > 0 && (
            <div className="section-card">
              <div className="section-title"><span className="icon">🚀</span> Projects</div>
              {s.projects.map((p, i) => (
                <div className="timeline-item" key={i}>
                  <div className="timeline-dot" />
                  <div className="timeline-title">{p.title} {p.link && <a href={p.link} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem' }}>↗</a>}</div>
                  {p.duration && <div className="timeline-duration">{p.duration}</div>}
                  {p.description && <div className="timeline-desc">{p.description}</div>}
                  {p.tools && <div className="timeline-tools">{p.tools.split(';').map(t => <span key={t} className="badge">{t.trim()}</span>)}</div>}
                </div>
              ))}
            </div>
          )}

          {/* Research */}
          {s.ind_projects?.length > 0 && (
            <div className="section-card">
              <div className="section-title"><span className="icon">🔬</span> Research / BTP Projects</div>
              {s.ind_projects.map((p, i) => (
                <div className="timeline-item" key={i}>
                  <div className="timeline-dot" />
                  <div className="timeline-title">{p.title}</div>
                  {p.professor && <div className="timeline-subtitle">Under {p.professor}</div>}
                  {p.description && <div className="timeline-desc">{p.description}</div>}
                  {p.tools && <div className="timeline-tools">{p.tools.split(';').map(t => <span key={t} className="badge">{t.trim()}</span>)}</div>}
                </div>
              ))}
            </div>
          )}

          {/* Papers */}
          {s.papers?.length > 0 && (
            <div className="section-card">
              <div className="section-title"><span className="icon">📄</span> Research Papers</div>
              {s.papers.map((p, i) => (
                <div className="timeline-item" key={i}>
                  <div className="timeline-dot" />
                  <div className="timeline-title">{p.title}</div>
                  {p.published_in && <div className="timeline-subtitle">{p.published_in}</div>}
                  {p.status && <div className="timeline-duration">Status: {p.status}</div>}
                  {p.description && <div className="timeline-desc">{p.description}</div>}
                </div>
              ))}
            </div>
          )}

          {/* Skills & Tools */}
          <div className="section-card">
            <div className="section-title"><span className="icon">🛠️</span> Technologies & Tools</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {s.tools?.map(t => <span key={t} className="badge">{t}</span>)}
            </div>
            {s.languages?.length > 0 && (
              <>
                <div className="section-title" style={{ marginTop: 16 }}><span className="icon">💻</span> Programming Languages</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {s.languages.map(l => <span key={l} className="badge" style={{ borderColor: '#6366f140', color: '#818cf8' }}>{l}</span>)}
                </div>
              </>
            )}
          </div>

          {/* Awards, Coursework, POR */}
          {(s.awards || s.coursework || s.por || s.certifications) && (
            <div className="section-card">
              {s.awards && <><div className="section-title"><span className="icon">🏆</span> Awards</div><p style={{ fontSize: '0.88rem', lineHeight: 1.6, color: 'var(--text)' }}>{s.awards.replace(/;/g, '\n• ')}</p></>}
              {s.certifications && <><div className="section-title" style={{ marginTop: 16 }}><span className="icon">📜</span> Certifications</div><p style={{ fontSize: '0.88rem', lineHeight: 1.6, color: 'var(--text)' }}>{s.certifications.replace(/;/g, '\n• ')}</p></>}
              {s.coursework && <><div className="section-title" style={{ marginTop: 16 }}><span className="icon">📚</span> Relevant Coursework</div><div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{s.coursework.split(';').map(c => <span key={c} className="badge">{c.trim()}</span>)}</div></>}
              {s.por && <><div className="section-title" style={{ marginTop: 16 }}><span className="icon">👑</span> Positions of Responsibility</div><p style={{ fontSize: '0.88rem', lineHeight: 1.6, color: 'var(--text)' }}>{s.por.replace(/;/g, '\n• ')}</p></>}
            </div>
          )}
        </div>

        {/* RIGHT PANEL — SCORES */}
        <div className="profile-right">
          <div className="section-card">
            <div className="section-title"><span className="icon">📈</span> Skill Scores</div>
            {topScores.map(([k, v]) => (
              <div className="score-bar-row" key={k}>
                <span className="score-bar-label">{k.replace(/_/g, ' ')}</span>
                <div className="score-bar-track"><div className="score-bar-fill" style={{ width: `${v * 10}%` }} /></div>
                <span className="score-bar-value">{v}</span>
              </div>
            ))}
            {topScores.length === 0 && <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>No scores available</p>}
          </div>
        </div>
      </div>
    </>
  )
}
