# 🚀 Resume Hub: Semantic Search & AI Parser (Full-Stack)

A state-of-the-art semantic search system for resumes. This project transforms raw PDF resumes into a searchable, visualized knowledge base using structured data extraction, vector-based retrieval (FAISS), and AI-driven reasoning powered by **Google Gemini**.

---

## 📂 Project Structure

| Path | Description |
| :--- | :--- |
| `backend/` | FastAPI server, API logic, and core parser integration. |
| `frontend/` | React (Vite) dashboard with search, profile, and graph visualizations. |
| `output/` | High-fidelity JSON files produced by the parser. |
| `photos/` | Student profile photos (matched by name). |
| `linkedin_pdfs/` | Input directory for raw PDF resumes. |
| `resume_parser.py` | **The Engine**: Parses PDFs into structured JSON using a multi-call Gemini pipeline. |
| `resume_search.py` | **The Search Logic**: Semantic retrieval using Gemini Embeddings + FAISS. |
| `resume_index.faiss` | The local vector database. |
| `resume_metadata.json` | Candidate metadata for fast lookup. |

---

## ✨ Key Features

### 1. Robust AI Extraction Pipeline
Uses a 5-call **Gemini** pipeline to ensure extreme accuracy across:
- Identity & Contact Info
- Education & CGPA
- Detailed Work Experience & Projects
- Domain-specific scoring (0-10) across 30+ categories (ML, VLSI, Backend, etc.)

### 2. Full-Stack Dashboard
- **Dashboard**: High-level stats and grid view of all students.
- **AI Search**: Natural language querying with semantic matching and **AI Re-ranking** (provides a reason *why* each candidate fits).
- **Knowledge Graph**: Interactive visualization of skills, companies, and student connections.
- **Upload Portal**: Batch upload PDFs to automatically parse and index them in real-time.

### 3. Semantic Search & Reasoning
Uses `models/gemini-embedding-001` for vectorizing query intent. Results are then processed by `gemini-1.5-flash` to provide human-like reasoning for the rankings.

### 4. Resilient API Management
Implemented a `KeyRotator` to cycle through multiple Gemini API keys, ensuring high-volume parsing doesn't hit rate limits.

---

## 🔧 Setup & Deployment

### 1. Environment Variables
Create a `.env` file in the project root:
```bash
GEMINI_API_KEYS="key1,key2,key3"
```

### 2. Local Development
```bash
# Backend (Port 8000)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (Port 5173)
cd frontend
npm install
npm run dev
```

### 3. Docker Deployment
```bash
docker-compose up --build
```

### 4. Render.com
Connect your GitHub repo and use the provided `render.yaml` blueprint for one-click deployment.

---

## 🛠️ Technology Stack
- **AI**: Google Gemini (Flash, Pro, Embeddings).
- **Vector DB**: FAISS.
- **Backend**: Python, FastAPI.
- **Frontend**: React, Vite, Vis.js, Vanilla CSS.
- **Infrastructure**: Docker.

---
**Maintained by**: Antigravity AI
**Project**: BTP Resume Parser Portal
