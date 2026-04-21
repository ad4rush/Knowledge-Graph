# 🚀 Resume Semantic Search & Parser System (BTP Project)

This project is a state-of-the-art semantic search system for resumes. It uses a combination of structured data extraction (Gemini API), vector-based retrieval (FAISS), and AI-driven reasoning to find the perfect candidates for any natural language query.

---

## 📂 Folder Structure

| Path | Description |
| :--- | :--- |
| `linkedin_pdfs/` | Input directory for raw PDF resumes (LinkedIn exports or standard PDFs). |
| `manual_text/` | Alternative input directory for resumes in JSON/text format. |
| `output/` | High-fidelity JSON files produced by the parser, containing rich structured data. |
| `resume_parser.py` | **The Engine**: Parses PDFs into structured JSON and auto-updates the search index. |
| `resume_search.py` | **The Interface**: The main tool for querying the resume database. |
| `resume_indexer.py` | **The Sync Tool**: Rebuilds or syncs the FAISS index from all existing JSON files. |
| `resume_index.faiss` | The local vector database storing 3072-dimensional embeddings. |
| `resume_metadata.json` | Stores candidate metadata and distilled text for fast lookup. |

---

## ✨ Features Implemented

### 1. Robust 5-Call Extraction Pipeline
Instead of one giant prompt, the `resume_parser.py` uses 5 specialized API calls to ensure extreme accuracy:
- **Call 1**: Basic Identity & Contact Info.
- **Call 2**: Detailed Education & Institutional data.
- **Call 3**: Academic Marks, CGPA, and Ranks.
- **Call 4**: Deep dive into Work Experience and Projects.
- **Call 5**: Domain-specific scoring (0-10) across 30+ technical categories (e.g., ML, VLSI, Frontend).

### 2. Semantic Search with FAISS
We use Facebook AI Similarity Search (FAISS) to perform sub-millisecond vector lookups.
- **Model**: `gemini-embedding-001` (3072 dimensions).
- **Technique**: L2-normalized Inner Product similarity.

### 3. Intelligent Distillation
To stay within Gemini's 2,048 token embedding limit, we implemented a custom "Distiller." It strips away JSON boilerplate and keeps only high-signal data (skill scores, truncated project descriptions, tools), reducing size by ~70% while retaining semantic meaning.

### 4. AI Re-ranking & Reasoning
The system doesn't just return a list; it *thinks*. When you query, it:
1. Finds the top 15 matches via vector search.
2. Passes them to **Gemini 2.5 Flash**.
3. The LLM acts as a **Technical Recruiter**, re-ranking the candidates and providing a specific reason *why* they fit your query.

### 5. Robust Key Rotation System
Since API quotas are a bottleneck, we built a `KeyRotator` class that:
- Cycles through **110+ API keys**.
- Automatically detects and skips `429 (Quota)`, `403 (Suspended)`, or `401 (Expired)` errors.
- Ensures the system never crashes during bulk processing.

### 6. Fully Automated Workflow (Incremental Indexing)
The parser and indexer are now merged. When you run `resume_parser.py` on a new batch of PDFs, it **automatically** generates the embedding and updates the FAISS index and metadata files in real-time.

---

## 💻 How to Use

### 1. Parsing & Indexing Resumes
Place your PDFs in `linkedin_pdfs/` and run:
```bash
python resume_parser.py --input_dir linkedin_pdfs --output_dir output --model gemini-2.5-flash
```

### 2. Searching for Candidates
Use natural language queries to find talent:
```bash
# General search
python resume_search.py "who knows machine learning the best"

# Specific tech stack
python resume_search.py "frontend developer with React and TypeScript experience"

# Domain specific
python resume_search.py "someone with experience in VLSI design and hardware"
```

---

## 🛠️ Technical Stack
- **AI Models**: Google Gemini (Pro, Flash, Embedding).
- **Vector DB**: FAISS (Facebook AI Similarity Search).
- **Data Processing**: Python, NumPy, pdfplumber.
- **Schema**: Custom "Rich-Flat" JSON for college-specific resumes.
