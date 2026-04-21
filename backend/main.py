#!/usr/bin/env python3
"""
FastAPI Backend for Resume Parser Portal
Serves student data, search, upload, photos, and knowledge graph data.
"""

import os
import sys
import json
import glob
import shutil
import re
import time
import subprocess
import numpy as np
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import faiss
import google.generativeai as genai

# ─── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = BASE_DIR / "output"
MANUAL_DIR  = BASE_DIR / "manual_text"
PHOTOS_DIR  = BASE_DIR / "photos"
PDF_DIR     = BASE_DIR / "linkedin_pdfs"
INDEX_FILE  = BASE_DIR / "resume_index.faiss"
META_FILE   = BASE_DIR / "resume_metadata.json"
EMBED_MODEL = "models/gemini-embedding-001"
LLM_MODEL   = "gemini-2.5-flash"

# ─── API KEYS ─────────────────────────────────────────────────────────────────
def get_api_keys() -> list:
    """Get API keys from env or fallback to hardcoded ones."""
    env_keys = os.getenv("GEMINI_API_KEYS", "").strip()
    if env_keys:
        return [k.strip() for k in env_keys.split(",") if k.strip()]
    single = os.getenv("GEMINI_API_KEY", "").strip()
    if single:
        return [single]
    # Fallback: read from resume_search.py's API_KEYS list
    search_file = BASE_DIR / "resume_search.py"
    if search_file.exists():
        content = search_file.read_text(encoding="utf-8")
        keys = re.findall(r'"(AIza[A-Za-z0-9_-]{33,})"', content)
        if keys:
            return keys
    return []

API_KEYS = get_api_keys()

# ─── KEY ROTATOR ──────────────────────────────────────────────────────────────
class KeyRotator:
    def __init__(self, keys):
        self.keys = keys if keys else [""]
        self.idx = 0

    def call_api(self, func, *args, **kwargs):
        tried = 0
        last_error = None
        while tried < len(self.keys):
            key = self.keys[self.idx % len(self.keys)]
            self.idx += 1
            tried += 1
            try:
                genai.configure(api_key=key)
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if any(x in err for x in ["429", "quota", "rate", "exhausted", "expired", "not found"]):
                    continue
        raise RuntimeError(f"All keys failed. Last error: {last_error}")

rotator = KeyRotator(API_KEYS)

# ─── SKILL CATEGORIES ────────────────────────────────────────────────────────
SKILL_CATEGORIES = [
    "webdev", "frontend", "backend", "mobile_dev", "app_dev",
    "cloud", "devops", "data_science", "machine_learning",
    "deep_learning", "reinforcement_learning", "computer_vision",
    "nlp", "cybersecurity_cryptography", "blockchain_web3",
    "bioinformatics", "ar_vr", "robotics_automation", "big_data",
    "digital_electronics", "analog_circuits", "vlsi_design",
    "embedded_systems", "signal_processing", "control_systems",
    "iot", "communication_systems", "power_systems_power_electronics",
    "quantum_computing", "digital_twins_simulation_tools"
]

# ─── FASTAPI APP ──────────────────────────────────────────────────────────────
app = FastAPI(title="Resume Parser Portal", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── MODELS ───────────────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str
    top: int = 5
    skip_llm: bool = False

class SearchResult(BaseModel):
    name: str
    score: float
    primary_domain: Optional[str] = None
    branch: Optional[str] = None
    photo_url: Optional[str] = None
    distilled: Optional[str] = None

class SearchResponse(BaseModel):
    candidates: list
    ai_analysis: Optional[str] = None

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def load_student_json(filepath: str) -> dict:
    """Load a single student JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_photo_filename(name: str) -> Optional[str]:
    """Find matching photo for a student name."""
    if not PHOTOS_DIR.exists():
        return None
    # Direct match
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        candidate = PHOTOS_DIR / f"{name}{ext}"
        if candidate.exists():
            return candidate.name
    # Fuzzy: try first name match
    name_lower = name.lower().strip()
    for photo in PHOTOS_DIR.iterdir():
        if photo.is_file() and photo.stem.lower().strip() == name_lower:
            return photo.name
    return None

def build_student_card(data: dict, source_file: str) -> dict:
    """Build a student card dict for the frontend."""
    name = data.get("name") or Path(source_file).stem
    
    # Get top scores
    scores = {}
    for cat in SKILL_CATEGORIES:
        score = data.get(f"{cat}_score")
        if score and isinstance(score, (int, float)) and score > 0:
            scores[cat] = score
    top_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5])
    
    # Work experience
    companies = []
    for i in range(1, 9):
        company = data.get(f"work_{i}_company")
        role = data.get(f"work_{i}_role")
        duration = data.get(f"work_{i}_duration")
        if company:
            companies.append({
                "company": company,
                "role": role,
                "duration": duration,
                "description": data.get(f"work_{i}_description"),
                "tools": data.get(f"work_{i}_tools"),
            })
    
    # Projects
    projects = []
    for i in range(1, 9):
        title = data.get(f"project_{i}_title")
        if title:
            projects.append({
                "title": title,
                "description": data.get(f"project_{i}_description"),
                "tools": data.get(f"project_{i}_tools"),
                "languages": data.get(f"project_{i}_languages"),
                "link": data.get(f"project_{i}_link"),
                "duration": data.get(f"project_{i}_duration"),
            })
    
    # Independent projects
    ind_projects = []
    for i in range(1, 6):
        title = data.get(f"indproj_{i}_title")
        if title:
            ind_projects.append({
                "title": title,
                "professor": data.get(f"indproj_{i}_professor"),
                "description": data.get(f"indproj_{i}_description"),
                "tools": data.get(f"indproj_{i}_tools"),
                "link": data.get(f"indproj_{i}_link"),
            })

    # Research papers
    papers = []
    for i in range(1, 7):
        title = data.get(f"paper_{i}_title")
        if title:
            papers.append({
                "title": title,
                "published_in": data.get(f"paper_{i}_published_in"),
                "status": data.get(f"paper_{i}_status"),
                "description": data.get(f"paper_{i}_description"),
            })

    # Tools/Languages
    tools_raw = data.get("net_tools_technologies") or data.get("tools_technologies_listed") or ""
    tools = [t.strip() for t in tools_raw.split(";") if t.strip()] if tools_raw else []
    
    langs_raw = data.get("net_known_languages") or data.get("programming_languages_listed") or ""
    languages = [l.strip() for l in langs_raw.split(";") if l.strip()] if langs_raw else []

    photo = get_photo_filename(name)

    return {
        "name": name,
        "source_file": source_file,
        "branch": data.get("branch"),
        "batch": data.get("batch"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "github_url": data.get("github_url"),
        "linkedin_url": data.get("linkedin_url"),
        "college": data.get("current_college_name") or data.get("ug1_college_name"),
        "cgpa": data.get("current_college_cgpa") or data.get("ug1_cgpa"),
        "primary_domain": data.get("primary_domain", "general"),
        "top_3_domains": data.get("top_3_domains", ""),
        "photo_url": f"/api/photos/{photo}" if photo else None,
        "all_scores": scores,
        "top_scores": top_scores,
        "companies": companies,
        "projects": projects,
        "ind_projects": ind_projects,
        "papers": papers,
        "tools": tools,
        "languages": languages,
        "awards": data.get("awards_list"),
        "certifications": data.get("certifications_list"),
        "coursework": data.get("relevant_coursework") or data.get("coursework_listed"),
        "por": data.get("por_positions_list"),
        "raw_data": data,
    }

# ─── CACHE ────────────────────────────────────────────────────────────────────
_students_cache = None
_cache_time = 0

def get_all_students(force_reload=False) -> list:
    global _students_cache, _cache_time
    if not force_reload and _students_cache and (time.time() - _cache_time) < 60:
        return _students_cache
    
    students = []
    seen_names = set()
    
    # Output dir (rich schema)
    if OUTPUT_DIR.exists():
        for fp in sorted(OUTPUT_DIR.glob("*.json")):
            try:
                data = load_student_json(str(fp))
                card = build_student_card(data, str(fp.relative_to(BASE_DIR)))
                if card["name"] not in seen_names:
                    seen_names.add(card["name"])
                    students.append(card)
            except Exception as e:
                print(f"Error loading {fp}: {e}")
    
    # Manual dir (LinkedIn schema) — only add if not already from output
    if MANUAL_DIR.exists():
        for fp in sorted(MANUAL_DIR.glob("*.json")):
            try:
                data = load_student_json(str(fp))
                name = data.get("student_name") or data.get("name") or fp.stem
                if name in seen_names:
                    continue
                # Adapt manual schema
                adapted = {
                    "name": name,
                    "branch": data.get("branch"),
                    "primary_domain": "general",
                }
                # Extract skills from manual schema
                skills_raw = data.get("skills", "")
                if skills_raw:
                    adapted["net_tools_technologies"] = ";".join(
                        [s.strip() for s in skills_raw.split("\n") 
                         if s.strip() and "endorsement" not in s.lower() 
                         and "experience" not in s.lower()
                         and "associated" not in s.lower()][:20]
                    )
                card = build_student_card(adapted, str(fp.relative_to(BASE_DIR)))
                seen_names.add(card["name"])
                students.append(card)
            except Exception as e:
                print(f"Error loading manual {fp}: {e}")
    
    _students_cache = students
    _cache_time = time.time()
    return students

# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "students": len(get_all_students()), "index_exists": INDEX_FILE.exists()}

@app.get("/api/students")
def list_students():
    """Return all student profiles."""
    students = get_all_students()
    # Return without raw_data to keep response small
    return [
        {k: v for k, v in s.items() if k != "raw_data"}
        for s in students
    ]

@app.get("/api/students/{name}")
def get_student(name: str):
    """Return a single student profile by name."""
    students = get_all_students()
    # URL-decode and match
    name_clean = name.replace("_", " ").replace("%20", " ").strip()
    for s in students:
        if s["name"].lower() == name_clean.lower():
            return s
    raise HTTPException(status_code=404, detail=f"Student '{name_clean}' not found")

@app.get("/api/photos/{filename}")
def get_photo(filename: str):
    """Serve a student photo."""
    photo_path = PHOTOS_DIR / filename
    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(str(photo_path))

@app.post("/api/search")
def search_students(req: SearchRequest):
    """Semantic search using FAISS + optional LLM re-ranking."""
    if not INDEX_FILE.exists() or not META_FILE.exists():
        raise HTTPException(status_code=400, detail="Index not built yet. Upload resumes first.")
    
    if not API_KEYS:
        raise HTTPException(status_code=500, detail="No API keys configured. Set GEMINI_API_KEYS env.")
    
    # Load index and metadata
    index = faiss.read_index(str(INDEX_FILE))
    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    # Embed query
    def _embed():
        return genai.embed_content(
            model=EMBED_MODEL,
            content=req.query,
            task_type="RETRIEVAL_QUERY",
        )
    
    try:
        result = rotator.call_api(_embed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")
    
    vec = np.array(result["embedding"], dtype="float32")
    vec /= np.linalg.norm(vec) + 1e-10
    vec = vec.reshape(1, -1)
    
    # Search — fetch extra to account for deduplication
    k = min(req.top * 3, len(metadata))
    distances, indices = index.search(vec, k)
    
    candidates = []
    seen_names = set()
    for i, dist in zip(indices[0], distances[0]):
        if i == -1:
            continue
        m = metadata[i]
        name = m.get("name", "")
        # Deduplicate by name (metadata may have dupes from output/ + manual_text/)
        if name in seen_names:
            continue
        seen_names.add(name)
        photo = get_photo_filename(name)
        candidates.append({
            "name": name,
            "score": float(dist),
            "primary_domain": m.get("primary_domain"),
            "branch": m.get("branch"),
            "cgpa": m.get("cgpa"),
            "top_domains": m.get("top_domains"),
            "distilled": m.get("distilled", ""),
            "photo_url": f"/api/photos/{photo}" if photo else None,
        })
        if len(candidates) >= req.top:
            break
    
    ai_analysis = None
    if not req.skip_llm and candidates:
        # Build LLM prompt
        context = ""
        for idx, c in enumerate(candidates):
            context += f"--- CANDIDATE {idx+1}: {c['name']} ---\n"
            context += f"Profile Info:\n{c['distilled']}\n\n"
        
        prompt = f"""You are an expert technical recruiter analyzing a list of candidates returned by a semantic search engine.
The user's query is: "{req.query}"

I am providing you with the top {len(candidates)} candidates that matched the query based on vector similarity.
Your job is to read their profiles, RE-RANK them strictly based on how well they actually fit the user's query, and pick the best ones.

Here are the candidates:
{context}

Please provide a final ranked list of the best fits. For each candidate, provide:
1. Rank number
2. Candidate Name  
3. A 1-2 sentence specific reason explaining WHY they are a good fit for this query, referencing their actual projects/skills.

Format the output cleanly. Do not hallucinate skills they don't have. If a candidate is a weak fit despite being in the list, you can skip them or mention they are a partial fit."""

        try:
            def _generate():
                model = genai.GenerativeModel(LLM_MODEL)
                return model.generate_content(prompt)
            
            response = rotator.call_api(_generate)
            ai_analysis = response.text
        except Exception as e:
            ai_analysis = f"LLM re-ranking failed: {e}"
    
    return {"candidates": candidates, "ai_analysis": ai_analysis}

@app.post("/api/upload")
async def upload_resumes(files: List[UploadFile] = File(...)):
    """Upload PDF resumes, parse them, and update the index."""
    if not PDF_DIR.exists():
        PDF_DIR.mkdir(parents=True, exist_ok=True)
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    saved_files = []
    
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            results.append({"file": file.filename, "status": "error", "message": "Not a PDF"})
            continue
        
        # Save PDF
        dest = PDF_DIR / file.filename
        with open(dest, "wb") as f:
            content = await file.read()
            f.write(content)
        saved_files.append(str(dest))
        results.append({"file": file.filename, "status": "saved", "message": "PDF saved"})
    
    # Run parser on all saved files
    if saved_files:
        try:
            parser_script = BASE_DIR / "resume_parser.py"
            cmd = [
                sys.executable, str(parser_script),
                "--input_dir", str(PDF_DIR),
                "--output_dir", str(OUTPUT_DIR),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(BASE_DIR))
            
            if proc.returncode == 0:
                for r in results:
                    if r["status"] == "saved":
                        r["status"] = "parsed"
                        r["message"] = "PDF parsed and indexed successfully"
            else:
                for r in results:
                    if r["status"] == "saved":
                        r["status"] = "parse_error"
                        r["message"] = f"Parser error: {proc.stderr[:200]}"
        except subprocess.TimeoutExpired:
            for r in results:
                if r["status"] == "saved":
                    r["status"] = "timeout"
                    r["message"] = "Parser timed out"
        except Exception as e:
            for r in results:
                if r["status"] == "saved":
                    r["status"] = "error"
                    r["message"] = str(e)
    
    # Invalidate cache
    global _students_cache
    _students_cache = None
    
    return {"results": results, "total_uploaded": len(saved_files)}

@app.get("/api/graph")
def get_graph_data():
    """Return knowledge graph data as JSON for frontend rendering."""
    students = get_all_students()
    
    nodes = []
    edges = []
    domain_hubs = set()
    tool_freq = {}
    company_freq = {}
    
    # Process students
    for s in students:
        domain = (s.get("primary_domain") or "general").lower().replace(" ", "_")
        domain_hubs.add(domain)
        
        for t in s.get("tools", []):
            tool_freq[t] = tool_freq.get(t, 0) + 1
        
        for c in s.get("companies", []):
            comp_name = c.get("company", "")
            if comp_name:
                company_freq[comp_name] = company_freq.get(comp_name, 0) + 1
    
    domain_colors = {
        'backend': '#6366f1', 'machine_learning': '#f59e0b', 'vlsi_design': '#10b981',
        'data_science': '#3b82f6', 'nlp': '#8b5cf6', 'computer_vision': '#ec4899',
        'embedded_systems': '#14b8a6', 'devops': '#f97316', 'deep_learning': '#a855f7',
        'cloud': '#06b6d4', 'general': '#94a3b8', 'webdev': '#ef4444',
        'digital_electronics': '#059669', 'analog_circuits': '#34d399',
        'signal_processing': '#6ee7b7', 'frontend': '#fb923c',
    }
    
    # Domain nodes
    for d in domain_hubs:
        count = sum(1 for s in students if (s.get("primary_domain") or "general").lower().replace(" ", "_") == d)
        nodes.append({
            "id": f"domain_{d}",
            "label": d.upper().replace("_", " "),
            "group": "domain",
            "size": min(30 + count * 3, 70),
            "color": domain_colors.get(d, "#94a3b8"),
            "count": count,
        })
    
    # Tool nodes (freq >= 2)
    for t, count in tool_freq.items():
        if count >= 2:
            nodes.append({
                "id": f"tool_{t}",
                "label": t,
                "group": "tool",
                "size": min(15 + count * 2, 45),
                "color": "#14b8a6",
                "count": count,
            })
    
    # Company nodes
    for c, count in company_freq.items():
        nodes.append({
            "id": f"comp_{c}",
            "label": c,
            "group": "company",
            "size": min(15 + count * 4, 50),
            "color": "#f59e0b",
            "count": count,
        })
    
    # Student nodes + edges
    for s in students:
        sid = f"std_{s['name'].replace(' ', '_').replace('.', '')}"
        photo = s.get("photo_url")
        nodes.append({
            "id": sid,
            "label": s["name"],
            "group": "student",
            "size": 15,
            "color": "#e2e8f0",
            "photo": photo,
            "domain": (s.get("primary_domain") or "general").lower().replace(" ", "_"),
            "top_scores": s.get("top_scores", {}),
        })
        
        # Student -> Domain
        domain = (s.get("primary_domain") or "general").lower().replace(" ", "_")
        edges.append({
            "from": sid,
            "to": f"domain_{domain}",
            "color": domain_colors.get(domain, "#94a3b8"),
        })
        
        # Student -> Tools
        for t in s.get("tools", []):
            if tool_freq.get(t, 0) >= 2:
                edges.append({
                    "from": sid,
                    "to": f"tool_{t}",
                    "color": "#14b8a6",
                    "dashes": True,
                })
        
        # Student -> Companies
        for c in s.get("companies", []):
            comp_name = c.get("company", "")
            if comp_name:
                edges.append({
                    "from": sid,
                    "to": f"comp_{comp_name}",
                    "color": "#f59e0b",
                })
    
    return {"nodes": nodes, "edges": edges}

@app.get("/api/stats")
def get_stats():
    """Return aggregate statistics for the dashboard."""
    students = get_all_students()
    
    domain_counts = {}
    total_with_work = 0
    total_with_projects = 0
    companies = set()
    
    for s in students:
        domain = s.get("primary_domain", "general")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        if s.get("companies"):
            total_with_work += 1
            for c in s["companies"]:
                companies.add(c.get("company", ""))
        if s.get("projects"):
            total_with_projects += 1
    
    return {
        "total_students": len(students),
        "total_with_work": total_with_work,
        "total_with_projects": total_with_projects,
        "total_companies": len(companies),
        "domain_distribution": domain_counts,
        "index_vectors": faiss.read_index(str(INDEX_FILE)).ntotal if INDEX_FILE.exists() else 0,
    }

# ─── SERVE FRONTEND (production) ─────────────────────────────────────────────
frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
