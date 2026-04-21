import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', icon: '📊', label: 'Dashboard' },
  { to: '/search', icon: '🔍', label: 'AI Search' },
  { to: '/graph', icon: '🕸️', label: 'Knowledge Graph' },
  { to: '/upload', icon: '📤', label: 'Upload Resumes' },
]

export default function Layout() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">Resume Parser</div>
        <nav className="sidebar-nav">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div style={{ padding: '0 24px', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
          BTP Project · IIIT-D
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
