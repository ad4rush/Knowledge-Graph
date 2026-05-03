import { useState, useEffect, useRef } from 'react'
import { fetchGraphData } from '../api'
import { DataSet, Network } from 'vis-network/standalone'

const domainColors = {
  backend: '#6366f1', machine_learning: '#f59e0b', vlsi_design: '#10b981',
  data_science: '#3b82f6', nlp: '#8b5cf6', computer_vision: '#ec4899',
  embedded_systems: '#14b8a6', devops: '#f97316', deep_learning: '#a855f7',
  cloud: '#06b6d4', general: '#94a3b8', webdev: '#ef4444',
  digital_electronics: '#059669', analog_circuits: '#34d399',
}

export default function Graph() {
  const containerRef = useRef(null)
  const networkRef = useRef(null)
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [searchVal, setSearchVal] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const nodesDataRef = useRef(null)
  const edgesDataRef = useRef(null)
  const rawNodesRef = useRef([])

  useEffect(() => {
    fetchGraphData().then(setGraphData).catch(console.error).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!graphData || !containerRef.current) return

    const nodesList = graphData.nodes.map(n => {
      const shapes = { domain: 'hexagon', tool: 'diamond', company: 'box', student: 'dot' }
      const fontColors = { domain: '#fff', company: '#000', tool: '#c5c6c7', student: '#fff' }
      return {
        id: n.id, label: n.label, shape: shapes[n.group] || 'dot',
        size: n.size || 15,
        color: { background: n.color, border: n.group === 'domain' ? '#fff' : n.color },
        font: { color: fontColors[n.group] || '#fff', size: n.group === 'domain' ? 18 : 12, bold: n.group === 'domain' },
        group: n.group, baseColor: n.color, rawData: n,
      }
    })
    rawNodesRef.current = nodesList

    const edgesList = graphData.edges.map((e, i) => ({
      id: `e_${i}`, from: e.from, to: e.to,
      color: { color: 'rgba(255,255,255,0.03)', highlight: e.color },
      width: 1, hidden: true, dashes: e.dashes || false, baseColor: e.color,
    }))

    nodesDataRef.current = new DataSet(nodesList)
    edgesDataRef.current = new DataSet(edgesList)

    const net = new Network(containerRef.current, { nodes: nodesDataRef.current, edges: edgesDataRef.current }, {
      nodes: { borderWidth: 2 },
      edges: { smooth: { type: 'continuous' } },
      physics: {
        barnesHut: { gravitationalConstant: -4000, centralGravity: 0.05, springLength: 250, springConstant: 0.01, damping: 0.09, avoidOverlap: 0.1 },
        maxVelocity: 50, solver: 'barnesHut', timestep: 0.35, stabilization: { iterations: 200 },
      },
      interaction: { hover: true, tooltipDelay: 200 },
    })

    net.on('click', params => {
      if (params.nodes.length > 0) spotlight(params.nodes[0])
      else resetSpotlight()
    })

    networkRef.current = net
    return () => net.destroy()
  }, [graphData])

  function spotlight(nodeId) {
    const net = networkRef.current
    const nodes = nodesDataRef.current
    const edges = edgesDataRef.current
    if (!net || !nodes || !edges) return

    const focalNode = nodes.get(nodeId)
    if (focalNode?.group === 'student') setSelected(focalNode.rawData)
    else setSelected(null)

    const connEdgeIds = net.getConnectedEdges(nodeId)
    const connNodeIds = new Set([nodeId])
    connEdgeIds.forEach(eid => { const e = edges.get(eid); if (e) { connNodeIds.add(e.from); connNodeIds.add(e.to) } })

    nodes.update(rawNodesRef.current.map(n => ({
      id: n.id,
      color: connNodeIds.has(n.id)
        ? { background: n.baseColor, border: '#fff' }
        : { background: 'rgba(60,60,60,0.3)', border: 'rgba(60,60,60,0.1)' },
      font: { color: connNodeIds.has(n.id) ? '#fff' : 'rgba(100,100,100,0.5)' },
    })))

    const allEdges = edges.get()
    edges.update(allEdges.map(e => ({
      id: e.id,
      hidden: !(e.from === nodeId || e.to === nodeId),
      color: (e.from === nodeId || e.to === nodeId) ? { color: e.baseColor } : e.color,
      width: (e.from === nodeId || e.to === nodeId) ? 2 : 1,
    })))

    net.focus(nodeId, { scale: 1.2, animation: { duration: 500, easingFunction: 'easeInOutQuad' } })
  }

  function resetSpotlight() {
    const nodes = nodesDataRef.current
    const edges = edgesDataRef.current
    if (!nodes || !edges) return
    setSelected(null)
    nodes.update(rawNodesRef.current.map(n => ({ id: n.id, color: { background: n.baseColor, border: n.group === 'domain' ? '#fff' : n.baseColor }, font: { color: n.group === 'company' ? '#000' : '#fff' } })))
    edges.update(edges.get().map(e => ({ id: e.id, hidden: true, width: 1 })))
    networkRef.current?.fit({ animation: { duration: 500 } })
  }

  useEffect(() => {
    if (!searchVal.trim() || !graphData) { setSuggestions([]); return }
    const val = searchVal.toLowerCase()
    const matches = graphData.nodes.filter(n => n.label.toLowerCase().includes(val)).slice(0, 8)
    setSuggestions(matches)
  }, [searchVal, graphData])

  if (loading) return <div><div className="spinner" /><p className="loading-text">Loading knowledge graph...</p></div>

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Knowledge Graph</h1>
        <p className="page-subtitle">Interactive visualization of students, skills, domains & companies</p>
      </div>

      <div style={{ position: 'relative', marginBottom: 16, maxWidth: 400 }}>
        <input className="search-input" style={{ paddingLeft: 16 }} placeholder="Search graph nodes..."
          value={searchVal} onChange={e => setSearchVal(e.target.value)} />
        {suggestions.length > 0 && (
          <div style={{ position: 'absolute', top: 52, left: 0, right: 0, background: 'rgba(31,40,51,0.95)', borderRadius: 12, border: '1px solid var(--border)', zIndex: 50, maxHeight: 250, overflowY: 'auto' }}>
            {suggestions.map(s => (
              <div key={s.id} style={{ padding: '10px 16px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}
                onClick={() => { spotlight(s.id); setSearchVal(s.label); setSuggestions([]) }}
                onMouseOver={e => e.currentTarget.style.background = 'var(--accent-glow)'}
                onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
                <span>{s.label}</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-dark)', textTransform: 'uppercase' }}>{s.group}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        <div className="graph-container" ref={containerRef} />
        {selected && (
          <div className="section-card" style={{ width: 300, flexShrink: 0, alignSelf: 'start', position: 'sticky', top: 32 }}>
            <div className="section-title">{selected.label}</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--accent)', textTransform: 'capitalize', marginBottom: 12 }}>
              {selected.domain?.replace(/_/g, ' ')}
            </div>
            {selected.top_scores && Object.entries(selected.top_scores).sort(([,a],[,b]) => b - a).slice(0, 5).map(([k, v]) => (
              <div className="score-bar-row" key={k}>
                <span className="score-bar-label">{k.replace(/_/g, ' ')}</span>
                <div className="score-bar-track"><div className="score-bar-fill" style={{ width: `${v * 10}%` }} /></div>
                <span className="score-bar-value">{v}</span>
              </div>
            ))}
            <button className="btn btn-primary" style={{ marginTop: 16, width: '100%' }}
              onClick={() => window.location.href = `/student/${encodeURIComponent(selected.label)}`}>
              View Full Profile →
            </button>
            <button className="btn btn-ghost" style={{ marginTop: 8, width: '100%' }} onClick={resetSpotlight}>
              Reset Spotlight
            </button>
          </div>
        )}
      </div>
    </>
  )
}
