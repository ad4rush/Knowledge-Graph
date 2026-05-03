import { useState, useRef } from 'react'
import { uploadResumes } from '../api'

export default function Upload() {
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState(null)
  const [dragover, setDragover] = useState(false)
  const inputRef = useRef()

  const handleFiles = (fileList) => {
    const pdfs = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith('.pdf'))
    setFiles(prev => [...prev, ...pdfs])
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragover(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleUpload = async () => {
    if (!files.length) return
    setUploading(true)
    setResults(null)
    try {
      const data = await uploadResumes(files)
      setResults(data)
      setFiles([])
    } catch (err) {
      setResults({ error: err.message })
    } finally {
      setUploading(false)
    }
  }

  const removeFile = (i) => setFiles(prev => prev.filter((_, idx) => idx !== i))

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Upload Resumes</h1>
        <p className="page-subtitle">Upload PDF resumes to auto-parse, index, and add to the knowledge base</p>
      </div>

      <div
        className={`upload-zone ${dragover ? 'dragover' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragover(true) }}
        onDragLeave={() => setDragover(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".pdf" multiple hidden onChange={e => handleFiles(e.target.files)} />
        <div className="upload-icon">📄</div>
        <div className="upload-text">Drop PDF resumes here or click to browse</div>
        <div className="upload-subtext">Supports batch upload · Files are parsed with Amazon Nova AI</div>
      </div>

      {files.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3 style={{ color: 'var(--text-bright)', marginBottom: 12 }}>
            {files.length} file{files.length > 1 ? 's' : ''} selected
          </h3>
          {files.map((f, i) => (
            <div key={i} className="upload-result-item">
              <span style={{ color: 'var(--text-bright)' }}>📄 {f.name}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>{(f.size / 1024).toFixed(0)} KB</span>
                <button className="btn btn-ghost" style={{ padding: '4px 10px', fontSize: '0.8rem' }} onClick={() => removeFile(i)}>✕</button>
              </div>
            </div>
          ))}
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={handleUpload} disabled={uploading}>
            {uploading ? '⏳ Parsing & Indexing...' : `🚀 Upload & Parse ${files.length} file${files.length > 1 ? 's' : ''}`}
          </button>
        </div>
      )}

      {uploading && (
        <div style={{ marginTop: 24 }}>
          <div className="spinner" />
          <p className="loading-text">Uploading PDFs → Parsing with Amazon Nova AI → Building embeddings → Updating FAISS index...</p>
        </div>
      )}

      {results && (
        <div className="upload-results" style={{ marginTop: 24 }}>
          <h3 style={{ color: 'var(--text-bright)', marginBottom: 12 }}>Results</h3>
          {results.error ? (
            <div style={{ color: 'var(--danger)', padding: 16, background: 'var(--bg-card)', borderRadius: 'var(--radius-sm)' }}>{results.error}</div>
          ) : (
            results.results?.map((r, i) => (
              <div key={i} className="upload-result-item">
                <span style={{ color: 'var(--text-bright)' }}>📄 {r.file}</span>
                <span className={`upload-status ${r.status === 'parsed' ? 'success' : r.status === 'saved' ? 'pending' : 'error'}`}>
                  {r.status === 'parsed' ? '✅ Parsed & Indexed' : r.status === 'saved' ? '⏳ Saved' : `❌ ${r.message}`}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </>
  )
}
