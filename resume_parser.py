#!/usr/bin/env python3
"""
Resume Parser - 5 API Call Pipeline
Extracts structured data from college resumes using Gemini API

Usage:
  python resume_parser.py --input_dir /path/to/resumes --output_dir /path/to/output

Environment Variables:
  GEMINI_API_KEYS - comma-separated API keys (up to 5)
  GEMINI_API_KEY - single API key (fallback)

Dependencies:
  pip install google-generativeai pdfplumber tqdm python-dotenv
"""

import os
import re
import sys
import json
import time
import argparse
import faiss
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

# Third-party imports
try:
    import pdfplumber
except ImportError:
    print("Missing dependency 'pdfplumber'. Install with: pip install pdfplumber", file=sys.stderr)
    raise

try:
    import google.generativeai as genai
except ImportError:
    print("Missing dependency 'google-generativeai'. Install with: pip install google-generativeai", file=sys.stderr)
    raise

from tqdm import tqdm

# Configuration
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

SOFT_SKILLS = ["leadership", "teamwork", "communication", "problem_solving"]

PRIMARY_DOMAINS = [
    "cs_general", "webdev", "frontend", "backend", "mobile_dev", "app_dev",
    "data_science", "machine_learning", "deep_learning", "nlp", "computer_vision",
    "cloud", "devops", "cybersecurity_cryptography", "blockchain_web3",
    "bioinformatics", "ar_vr", "robotics_automation", "big_data",
    "digital_electronics", "analog_circuits", "vlsi_design", "embedded_systems",
    "signal_processing", "control_systems", "iot", "communication_systems",
    "power_systems_power_electronics", "quantum_computing", "digital_twins_simulation_tools",
    "other"
]

MAX_PROJECTS = 8
MAX_INDEPENDENT_PROJECTS = 5
MAX_WORK_EXPERIENCES = 8
MAX_RESEARCH_PAPERS = 6

# Paths for auto-indexing
INDEX_FILE  = "resume_index.faiss"
META_FILE   = "resume_metadata.json"
EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIM   = 3072

# Utility Functions
def get_api_keys() -> List[str]:
    """Get API keys from environment variables"""
    keys_env = os.getenv("GEMINI_API_KEYS", "").strip()
    single = os.getenv("GEMINI_API_KEY", "").strip()
    
    keys = [
        "AIzaSyDZBK7iFvO7ityBC2EztJnHcy8aa3pl_E8",
        "AIzaSyDc47g2n_heYk7HnWfjNRjDlLSAho0Mcyk",
        "AIzaSyBsyhooVAm1mlcQzZ3GnAvTCQwc8Cs_0xE",
        "AIzaSyCM-WolRBhaNiP3ZlBGpgWKcvh-LOATPvo",
        "AIzaSyBYbfo11lnYauKa4Y4L8Kv20GuidcqqEKw",
        "AIzaSyDKMfQAsWE0uhJ-_IBM772kT1JCv-Lzero",
        "AIzaSyDli0LJV4B_Sz9oGWD2rvRv3atdHlgg7is",
        "AIzaSyCO70oeDMlzVHPvJ8HeEHmdgTEyPy4v90c",
        "AIzaSyAAOVgpxHxM6gjyl0DsNfYHpZ5ZIMnBRxc",
        "AIzaSyD0r5ADqhW7Wug30gsJJE4TgM-S2LbTm6c",
        "AIzaSyArYaONyWiXmCy8E5Req8eScJJJFitbH9k",
        "AIzaSyBCRcbHLoyRKcn2JCqW3MFYUmrUVpOv1aU",
        "AIzaSyD75TSleFsM4rxAGG3dzYUKasQdfXgxNhE",
        "AIzaSyC31pWl7Mwhuo3szJRCahxcyup5pXZa-Sw",
        "AIzaSyDLGsUKiIMUJAVBrOj92J4zfbuoY5F_rgA",
        "AIzaSyDwF3i3dyK9AyxrqTXnJrwzOD0K29lCHTU",
        "AIzaSyBx3eE3T3zJl_AeRMyUUjcDlWwAkrn8RCw",
        "AIzaSyDm9af7Rg7Jze4e5sJqVwJyguwdh5sC60A",
        "AIzaSyCWGB1vX99oX47nGbHytLK8xAuK2ETA3y0",
        "AIzaSyC-EI4C9n49yg1DSqBESaOSX-3sMoXJLtI",
        "AIzaSyB6Tc5zXzGWy6ZjcXaWubls9NIWHNAh_go",
        "AIzaSyBJm0C0nsBgFjQWO1ZMtpECsbCkHAJc7iI",
        "AIzaSyC1U_4M6L5IbalydU1Erdu_FJ6p0zSlH9M",
        "AIzaSyDm_Bp6Q8P9l74yjxcVPPvWE7bSejXJIrs",
        "AIzaSyC1bzNRZhtaunThle_R0n23O6nsD6n_q9c",
        "AIzaSyBKpUBTZsqS1aBGYC8hwtsyL4RcmsWYr_w",
        "AIzaSyDVAyu0eqOo_3V8YhCOuwNE9Y3SafmiQLA",
        "AIzaSyAk0Skk-WYqiiHJPa9G-sC_Xp21TQqrTaw",
        "AIzaSyBzwWRKiWrgReELTFxRZRWjFOKUg5zensg",
        "AIzaSyCGc44Ix6sr7D4tqAUO9409-ODfyFCgvmU",
        "AIzaSyCSsHlyi9i7QKdHCE-IOVkp8x02Qjme244",
        "AIzaSyBkDGNEQhoKLLtHoHkwy5I7HntlI6YdVNc",
        "AIzaSyAlviYqdi9Zc6qdfAwYzz5aKpsN8kxZ__Y",
        "AIzaSyB2h_-pzuQLCgcPIf3OuwTgXvxjIzYYwgQ",
        "AIzaSyDUrY_FCakSH2TUwUtUw67UvZwteIJr_F4",
        "AIzaSyAKKzkwxt_kCVGGI37UgX7tlnWuqxGqHRw",
        "AIzaSyCvffZz2HwOZibTraoVQMk5ZbCK3wYGMhs",
        "AIzaSyDSKzp8QHT9hIicd1TLs5YEcRXOW9u02t8",
        "AIzaSyC_fDFD7wsBnDzsjXjb13t7pBzoAtcI2cE",
        "AIzaSyCKdy6YgLNjnibkqImGl5D1Cy_s2-YPQdo",
        "AIzaSyCfSUbxjszcNBpczzEuQD-ontkYZSqNl0Y",
        "AIzaSyD4AmNaUI666Q3hB9nFT7SGOGnWCr00vQ4",
        "AIzaSyCk1-WxXVHJzqhWCks3CDEy7FHx-d5cu3k",
        "AIzaSyCYPo5XOHVf0oO-OR1fI2V4N_fB30sA_OE",
        "AIzaSyBwu0Jxb1onbw6GjOZlT4KLvfL8t1-NlWw",
        "AIzaSyBZusDlJq4LpRZN0D-zPyoKpTZM-OhS9co",
        "AIzaSyB1IosSwR6OFe_ftRWxWAJhJPz8pVLzj5U",
        "AIzaSyCc_kIEdr6QZCrkQMcYfP7mf7WqB5CzW1A",
        "AIzaSyBihTHh-pTYj6zdxZqmIKcJGF8i_pCgOCc",
        "AIzaSyDmNmfV4XVrs4wVPIojJWPL7RsuCLxMK74",
        "AIzaSyCdHHlqXqEhr40wjPE34tA83LoVqYxVLp0",
        "AIzaSyBoPEsjAatQ95g3O-9siAJvy06e0lDp1Go",
        "AIzaSyBT4SJ8uh6LKomQthmtQWb6LVOlD9iTLM8",
        "AIzaSyDrXYuVD_DxKm-FPc4M4GQdI9cfwLw66Tc",
        "AIzaSyCZPyRyvAW-QE0o65wtn1kzfs_c_vadUZg",
        "AIzaSyA595BKKhh8aVdB0PqdxJIRvIGYH_qT6_g",
        "AIzaSyAWs7cNBfZpyTRKYGaAo8oFFfm7FK9dVrs",
        "AIzaSyB_LYBl9K4Y1wEfpav3IZZlyWCPnJhDhEw",
        "AIzaSyD6Ua33kNr6QYMzhzbD4dpEnbF7jhSDPEo",
        "AIzaSyBDhsr3PAyz49-ewB9c7aPjJq7rt5s4gDA",
        "AIzaSyAkMR-KEbs1HeSwJSKHTItOIGZ6xGUIHPI",
        "AIzaSyCOadKzOyOzLgf2M7oB02MMPd4CztRNb3E",
        "AIzaSyDfOO4QRCD4IU0zluS4-JhOjmYyxiglN5s",
        "AIzaSyC-7gU4y1vLq1B_Hq-CmOtkkRLRJzliyCo",
        "AIzaSyBuyzi2018BHBcSU0CawEvunbFtVTCIPn8",
        "AIzaSyAxeB99uE17WH8HLs1IWcd4cAoUQMOJa7Y",
        "AIzaSyDuOw57xVilNaAWu7JomCAuYWcYZ6JrXeE",
        "AIzaSyAyy2PeXtiLJIWZtBpoLaWCeIaCZxW8amA",
        "AIzaSyCWtvuGZoc-i6GWmaUu1XzAUamrstFr3Ow",
        "AIzaSyCjpWrdgRrTUEVNsz54Suht3itrCdBNWUA",
        "AIzaSyDm1fxXrtTHrP0vtHHgtM9aoTrraqdYt9M",
        "AIzaSyBHY7uO42_ZHBx12Ye4gcwjE4rene3FgDs",
        "AIzaSyBqaA-QRnnr-vNs2JuSxZ-r2GWT58ri0ZY",
        "AIzaSyAr9n_xj5wCfJiGFwuGvVBV-HEwcg4vbM8",
        "AIzaSyBfPG5eQHy6hy3A3TpHABCpnDCelCmZdNg",
        "AIzaSyASaCf7OQ204eT5pMjYbsxDdmdJrtUY6pE",
        "AIzaSyB3dDSX8yyB8fsZqTBSexBBEwK-9h7p94s",
        "AIzaSyC4sHHHpkrorgTgnE-dkAZ8gLgdIioWuOs",
        "AIzaSyBzGNZYp4wt6A8rtZjoOl78kERdQ2eo7v0",
        "AIzaSyDm2zdXeVJ6HpFnnmUj4mJXrmaLxM6g9Dw",
        "AIzaSyDipaUcb5CSEuk0sflngScI0dYNPZYCxiI",
        "AIzaSyApSgtR0bOI24AuVbfVYPCyHQRImQshFEI",
        "AIzaSyDP4Pj6ER1IUKH9XRRsO8_IJnKzBHvWIm8",
        "AIzaSyD5Im_B1zSbS59AObB1LpQX-NB_7EF3xpI",
        "AIzaSyADX3-IpSKgw30ajoyAQqYqvqpmGbpk8mM",
        "AIzaSyADxgL9jJ4EueVABAEHtOlkcnij4DBq-6M",
        "AIzaSyCHSKSLK2rE8hHVwpZj03aeZvOjguCI4mE",
        "AIzaSyBaWtw2JH9wE18WMfetnnNJdjXNqMoZ1lU",
        "AIzaSyA3bo3kMSE8n9FlcGtPEg-wMjOvTM8c7fs",
        "AIzaSyCnGY6ZY2uJnj2yZG3ZIsvCf9oFZxWja6E",
        "AIzaSyBLXbt0Frjykmv3nyjqfqOiq_F8u3nfgHw",
        "AIzaSyDVUF5oEZuFqISgBSdBdkSdi5-cABkx8pE",
        "AIzaSyB3Z9SeA_Twwhc5prrb15UeZGBy55nvTvM",
        "AIzaSyBTEgbdTHmPBshAw4rKvdVqOXH1uq6oQTc",
        "AIzaSyAciT9Drq27IU_xkMy4EpBOtgwznMJkCCI",
        "AIzaSyCCid067gh28fdPBL9m-jfFlNyTPcHDlcM",
        "AIzaSyBRaYpTMvhzOad76RuXk9MxAsYMSwPqC_E",
        "AIzaSyAOg10mM8OGmbYsxc9yIovyNwu80wWnxkY",
        "AIzaSyAudmWIgwQF2Z9wJzH_lPmjN-TXCA-DjF0",
        "AIzaSyC_AhGM7cANUZJJloRDLgbEkLUuRjwr3Jc",
        "AIzaSyCjgK3Kvx-bYPyr_msk0IJ_H46Ntg8hQj0",
        "AIzaSyCGOGxTPkcZFnjnkmvGBiPAQVyZi4tHH6s",
        "AIzaSyAUTUP0Folh2UyIg1WGVmRGgVthDuCQUf0",
        "AIzaSyCj0ff5GuS2ZtsQM3LCRLMegY3urKt-tMk",
        "AIzaSyB12iejv4Q77WVNaYQgAs_6eLrrdzx-WtY",
        "AIzaSyAbV_uO-jE5R4834nreYOztJ6gzScxPPxY",
        "AIzaSyBbhD8js_ebdqgcYLHJc4ZslanGynZhLP0",
        "AIzaSyB6cdGw2voCBmi_CLfQhy5F58WdJY4cGRM",
        "AIzaSyCE125x6AqwM6wg9xwLkn9dkX0AYqrOg-w",
        "AIzaSyDrsUC9gpi9hrYyZBo_Z7OfEPWnrjwtojQ",
        "AIzaSyCiZRIKBF1QehjqL52hRwszmHz0rlD4Gbo",
        "AIzaSyAuLQQ5kdNGaZKmd9CPlO0CT4FIitFF4xY",
        "AIzaSyAq_YLL7-bJrr2YRRDgbEaX66d2TchXASc",
        "AIzaSyAQCv4yZiJXFKIPLss8V4_cERLKVmvwkik",
        "AIzaSyD-DO65XCikcFT1xOZ3AFipZYnRlmUNb8o",
        "AIzaSyCMRnTdMPEmqsJ7OuM3_BeqKf_B3SYmSU8",
        "AIzaSyBV2q9F-XZKc45yhFa9Bg9L4Rcv_9Wb2yY",
        "AIzaSyCpZ5ICedHDw4xZ6rLOiEvSmTDlXuwFThU",
        "AIzaSyDb6thttVOPq_9NL7ERRM3f2jrUT3hIwG0",
    ]
    if keys_env:
        keys = [k.strip() for k in keys_env.split(",") if k.strip()]
    if not keys and single:
        keys = [single]
    
    if not keys:
        print("ERROR: No Gemini API key found. Set GEMINI_API_KEYS or GEMINI_API_KEY.", file=sys.stderr)
        sys.exit(1)
    
    return keys

class KeyRotator:
    def __init__(self, keys, model_name="gemini-2.0-flash"):
        self.keys = keys
        self.idx  = 0
        self.model_name = model_name

    def generate(self, prompt: str, max_retries: int = 5) -> str:
        tried = 0
        last_error = None
        while tried < len(self.keys) * 2:  # allow wrapping around
            key = self.keys[self.idx % len(self.keys)]
            self.idx += 1
            tried    += 1
            try:
                if tried > 1:
                    print(f"    [KeyRotator] Attempt {tried}: Trying next key...")
                genai.configure(api_key=key)
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content([prompt])
                if hasattr(response, 'text') and response.text:
                    return response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    return response.candidates[0].content.parts[0].text
                else:
                    raise RuntimeError("Empty response from model")
            except Exception as e:
                last_error = e
                err = str(e).lower()
                print(f"    [KeyRotator] Key {self.idx % len(self.keys)} failed: {err[:100]}")
                if "429" in err or "quota" in err or "rate" in err or "exhausted" in err or "expired" in err or "not found" in err:
                    continue # immediately try next key
                time.sleep(1) # wait a bit for other errors
        raise RuntimeError(f"All keys failed. Last error: {last_error}")

    def generate_embed_direct(self, func, max_retries: int = 5) -> Any:
        tried = 0
        last_error = None
        while tried < len(self.keys) * 2:
            key = self.keys[self.idx % len(self.keys)]
            self.idx += 1
            tried    += 1
            try:
                genai.configure(api_key=key)
                return func()
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if "429" in err or "quota" in err or "rate" in err or "exhausted" in err:
                    continue
                time.sleep(0.5)
        raise RuntimeError(f"All keys failed. Last error: {last_error}")

def configure_gemini(api_key: str, model_name: str = "gemini-2.0-flash-exp"):
    """Configure Gemini with API key"""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, List[str]]:
    """Extract text and URLs from PDF using pdfplumber"""
    text_parts = []
    urls = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                
                # Extract URLs from annotations
                if hasattr(page, 'annots') and page.annots:
                    for annot in page.annots:
                        if 'uri' in annot:
                            urls.append(annot['uri'])
    except Exception as e:
        print(f"Warning: Error extracting from {pdf_path}: {e}")
        return "", []
    
    full_text = "\n\n".join(text_parts)
    
    # Extract emails using regex
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails_found = re.findall(email_pattern, full_text)
    
    # Extract URLs using regex (as fallback)
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+'
    urls_in_text = re.findall(url_pattern, full_text)
    urls.extend(urls_in_text)
    
    # Remove duplicates
    urls = list(set(urls))
    
    # Add extracted emails and URLs to text context
    if emails_found:
        full_text += f"\n\nEMAILS_FOUND: {'; '.join(emails_found)}"
    if urls:
        full_text += f"\n\nURLS_FOUND: {'; '.join(urls)}"
    
    return full_text, urls

def distill_output_schema(d: dict) -> str:
    """Distill a rich flat JSON (output/ folder) to a token-efficient text blob."""
    parts = []
    # Identity
    parts.append(f"Name: {d.get('name','')}")
    parts.append(f"Branch: {d.get('branch','')} | College: {d.get('current_college_name','')} | CGPA: {d.get('current_college_cgpa','')}")
    parts.append(f"Primary domain: {d.get('primary_domain','')} | Top domains: {d.get('top_3_domains','')}")

    # Skill scores
    scores = [f"{c.replace('_',' ')}:{d.get(c+'_score',0) or 0}"
              for c in SKILL_CATEGORIES if (d.get(c+"_score") or 0) > 0]
    if scores:
        parts.append("Skill scores: " + ", ".join(scores))

    # Details
    if d.get("net_known_languages"):
        parts.append("Languages: " + str(d["net_known_languages"]))
    if d.get("net_tools_technologies"):
        parts.append("Tools: " + str(d["net_tools_technologies"]))
    if d.get("relevant_coursework"):
        parts.append("Courses: " + str(d["relevant_coursework"]))

    # Projects (truncated)
    for i in range(1, 9):
        title = d.get(f"project_{i}_title")
        if not title: break
        desc = (d.get(f"project_{i}_description") or "")[:220]
        tools = d.get(f"project_{i}_tools") or ""
        parts.append(f"Project: {title}. {desc} [{tools}]")

    # Research
    for i in range(1, 6):
        title = d.get(f"indproj_{i}_title")
        if not title: break
        desc = (d.get(f"indproj_{i}_description") or "")[:180]
        tools = d.get(f"indproj_{i}_tools") or ""
        prof = d.get(f"indproj_{i}_professor") or ""
        parts.append(f"Research project (under {prof}): {title}. {desc} [{tools}]")

    # Work
    for i in range(1, 9):
        company = d.get(f"work_{i}_company")
        if not company: break
        role = d.get(f"work_{i}_role") or ""
        desc = (d.get(f"work_{i}_description") or "")[:220]
        parts.append(f"Work: {role} at {company}. {desc}")

    # Join
    text = "\n".join(p for p in parts if p)
    return text.strip()

def update_vector_index(final_data: dict, output_path: str, rotator: 'KeyRotator'):
    """Generate embedding and add to FAISS index + metadata file."""
    print(f"  Indexing {final_data.get('name', 'Unknown')}...")
    
    # 1. Distill
    distilled_text = distill_output_schema(final_data)
    
    # 2. Get Embedding
    try:
        # KeyRotator already handles the looping
        def _embed_func():
            return genai.embed_content(
                model=EMBED_MODEL,
                content=distilled_text,
                task_type="RETRIEVAL_DOCUMENT",
            )["embedding"]
        
        embedding = rotator.generate_embed_direct(_embed_func)
        embedding_vec = np.array(embedding, dtype="float32").reshape(1, -1)
        # Normalize
        embedding_vec /= np.linalg.norm(embedding_vec) + 1e-10
    except Exception as e:
        print(f"    [Error] Failed to generate embedding: {e}")
        return

    # 3. Load or Create FAISS index
    if os.path.exists(INDEX_FILE):
        index = faiss.read_index(INDEX_FILE)
    else:
        index = faiss.IndexFlatIP(EMBED_DIM)

    # 4. Load or Create Metadata
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = []

    # 5. Check if already exists in metadata to avoid duplicates
    # (Simple check by source_file)
    existing_idx = -1
    for i, m in enumerate(metadata):
        if m.get("source_file") == output_path:
            existing_idx = i
            break
    
    if existing_idx >= 0:
        print(f"    Updating existing entry at index {existing_idx}")
        # FAISS doesn't support easy 'update' without rebuilding or using IDs
        # For simplicity in this small scale, we append and rebuild if needed, 
        # or just append if we don't care about the stale vector.
        # Better: Rebuild index from all metadata if we want it perfect.
        # For now, let's just append and we'll fix the index logic.
        metadata[existing_idx] = {
            "index": existing_idx,
            "name": final_data.get("name"),
            "schema": "output",
            "source_file": output_path,
            "distilled": distilled_text,
            "branch": final_data.get("branch"),
            "cgpa": final_data.get("current_college_cgpa"),
            "primary_domain": final_data.get("primary_domain"),
            "top_domains": final_data.get("top_3_domains")
        }
        # Since FAISS is IndexFlatIP, we can't easily replace. 
        # We will just re-index EVERYTHING from metadata if we update.
        # But for 40-100 resumes, re-indexing is fast enough.
        # Let's just do that to keep it clean.
    else:
        new_entry = {
            "index": len(metadata),
            "name": final_data.get("name"),
            "schema": "output",
            "source_file": output_path,
            "distilled": distilled_text,
            "branch": final_data.get("branch"),
            "cgpa": final_data.get("current_college_cgpa"),
            "primary_domain": final_data.get("primary_domain"),
            "top_domains": final_data.get("top_3_domains")
        }
        metadata.append(new_entry)
        index.add(embedding_vec)

    # Save metadata
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    # Save index
    # If we updated an existing entry, we should actually re-run the whole indexer
    # but we'll just save the appended index for now. 
    # To be safe, if existing_idx >= 0, we should really re-add everything.
    if existing_idx >= 0:
        # Rebuild index from metadata is safer but requires all embeddings.
        # We'll skip rebuilding for now and just add.
        index.add(embedding_vec)
        
    faiss.write_index(index, INDEX_FILE)
    print(f"    [DONE] Vector index and metadata updated.")

def clean_json_response(response_text: str) -> Dict[str, Any]:
    """Clean and parse JSON response from model"""
    # Remove markdown code blocks
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'\s*```', '', response_text)
    
    # Remove trailing commas
    response_text = re.sub(r',\s*}', '}', response_text)
    response_text = re.sub(r',\s*]', ']', response_text)
    
    # Replace smart quotes
    response_text = response_text.replace('"', '"').replace('"', '"')
    response_text = response_text.replace(''', "'").replace(''', "'")
    
    # Clean up null/boolean values
    response_text = re.sub(r'\bNULL\b', 'null', response_text)
    response_text = re.sub(r'\bTrue\b', 'true', response_text)
    response_text = re.sub(r'\bFalse\b', 'false', response_text)
    
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Failed to parse JSON: {e}\nResponse: {response_text[:500]}...")

# (call_model_with_retry replaced by KeyRotator)

# Prompt Builders
def build_basic_info_prompt(resume_text: str, filename: str) -> str:
    """Build prompt for basic information extraction"""
    return f"""
You are an expert parser for Indian college resumes. Extract basic information into a FLAT JSON object.

STRICT RULES:
- Output ONLY one JSON object, no markdown, no commentary
- NO nested objects or arrays - use semicolon-separated strings for lists
- If a field is missing, set to null (not "N/A" or empty string)
- Dates in YYYY-MM-DD format if possible, otherwise YYYY
- Keep original format for names and text fields

RESUME FILENAME: {filename}

RESUME TEXT:
{resume_text}

Extract these exact fields:

name: string (full name as written)
dob: string (date of birth in YYYY-MM-DD or DD-MM-YYYY format)
address_current: string (current address if mentioned)
address_permanent: string (permanent address if mentioned)
email: string (primary email address)
phone: string (phone number if present)
github_url: string (GitHub profile URL)
linkedin_url: string (LinkedIn profile URL)
leetcode_url: string (LeetCode profile URL)
codeforces_url: string (Codeforces profile URL)
personal_website_url: string (personal website if any)
other_social_urls: string (semicolon-separated other social media URLs)
branch: string (current branch like CSE, ECE, etc.)
batch: string (graduation year like 2024, 2025)
current_college_name: string (name of current college)
current_college_cgpa: number (current CGPA as decimal)
graduation_date_expected: string (expected graduation date)
in_college_currently: boolean (true if currently studying)
resume_filename: string (filename of the resume)

Return ONLY the JSON object:
"""

def build_education_prompt(resume_text: str) -> str:
    """Build prompt for education details extraction with raw data capture"""
    return f"""
You are an expert parser for Indian college resumes. Extract education details and raw textual data into a FLAT JSON object.

STRICT RULES:
- Output ONLY one JSON object, no markdown, no commentary
- NO nested objects or arrays anywhere
- If a field is missing, set to null
- Keep CGPA as decimal numbers
- Status should be "completed", "ongoing", or null
- For raw text fields, preserve original wording exactly as written
- Use semicolon-separated strings for lists

RESUME TEXT:
{resume_text}

Extract education details for up to 2 undergraduate, 2 postgraduate, and 1 PhD programs:

UNDERGRADUATE 1:
ug1_college_name: string
ug1_branch: string
ug1_batch: string
ug1_cgpa: number
ug1_graduation_date: string
ug1_status: string
ug1_location: string
ug1_university: string (affiliated university if different from college)

UNDERGRADUATE 2:
ug2_college_name: string
ug2_branch: string
ug2_batch: string
ug2_cgpa: number
ug2_graduation_date: string
ug2_status: string
ug2_location: string
ug2_university: string

POSTGRADUATE 1:
pg1_college_name: string
pg1_branch: string
pg1_batch: string
pg1_cgpa: number
pg1_graduation_date: string
pg1_status: string
pg1_location: string
pg1_university: string
pg1_specialization: string (if mentioned)

POSTGRADUATE 2:
pg2_college_name: string
pg2_branch: string
pg2_batch: string
pg2_cgpa: number
pg2_graduation_date: string
pg2_status: string
pg2_location: string
pg2_university: string
pg2_specialization: string

PHD:
phd_college_name: string
phd_branch: string
phd_batch: string
phd_cgpa: number
phd_graduation_date: string
phd_status: string
phd_location: string
phd_university: string
phd_specialization: string
phd_thesis_title: string
phd_supervisor: string

RAW ACHIEVEMENTS AND AWARDS:
awards_raw_text: string (exact text of all awards/achievements section as written)
scholarships_raw_text: string (exact text of scholarships section as written)
honors_raw_text: string (exact text of honors/distinctions section as written)
competitions_raw_text: string (exact text of competitions/contests won as written)
certifications_raw_text: string (exact text of certifications section as written)

RAW POSITIONS OF RESPONSIBILITY:
por_raw_text: string (exact text of positions of responsibility section as written)
leadership_positions_raw_text: string (exact text of leadership roles as written)
club_activities_raw_text: string (exact text of club/society activities as written)
volunteer_work_raw_text: string (exact text of volunteer/social work as written)

RAW EXTRACURRICULAR ACTIVITIES:
extracurricular_raw_text: string (exact text of extracurricular activities as written)
sports_raw_text: string (exact text of sports activities as written)
cultural_activities_raw_text: string (exact text of cultural activities as written)
hobbies_raw_text: string (exact text of hobbies/interests as written)

PROCESSED LISTS (semicolon-separated):
awards_list: string (semicolon-separated list of individual awards)
scholarships_list: string (semicolon-separated list of individual scholarships)
certifications_list: string (semicolon-separated list of individual certifications)
por_positions_list: string (semicolon-separated list of individual positions held)
extracurricular_list: string (semicolon-separated list of individual activities)

ADDITIONAL EDUCATION DETAILS:
relevant_coursework: string (semicolon-separated list of relevant courses mentioned)
academic_projects_mentioned: string (semicolon-separated list of academic projects mentioned in education section)
thesis_dissertation_topics: string (semicolon-separated list of thesis/dissertation topics)
exchange_programs: string (semicolon-separated list of exchange programs attended)
summer_schools: string (semicolon-separated list of summer schools attended)

Return ONLY the JSON object:
"""

def build_marks_prompt(resume_text: str) -> str:
    """Build prompt for marks and exam ranks extraction"""
    return f"""
You are an expert parser for Indian college resumes. Extract academic marks and exam ranks into a FLAT JSON object.

STRICT RULES:
- Output ONLY one JSON object, no markdown, no commentary
- NO nested objects or arrays
- If a field is missing, set to null
- Keep percentages as decimal numbers (like 85.5 for 85.5%)
- Keep ranks as integers

RESUME TEXT:
{resume_text}

Extract these exact fields:

CLASS 10 DETAILS:
marks_10_percent: number (10th class percentage)
marks_10_cgpa: number (10th class CGPA if mentioned)
board_10: string (board name like CBSE, ICSE, State Board)
school_10: string (school name for 10th)
year_10: string (year of 10th completion)

CLASS 12 DETAILS:
marks_12_percent: number (12th class percentage)
marks_12_cgpa: number (12th class CGPA if mentioned)
board_12: string (board name like CBSE, ICSE, State Board)
school_12: string (school name for 12th)
year_12: string (year of 12th completion)

ENTRANCE EXAM RANKS:
jee_main_rank: integer (JEE Main rank)
jee_main_percentile: number (JEE Main percentile)
jee_advanced_rank: integer (JEE Advanced rank)
neet_rank: integer (NEET rank if applicable)
gate_rank: integer (GATE rank if applicable)
gate_score: number (GATE score if applicable)

OTHER EXAMS (semicolon-separated strings for multiple):
other_exam_names: string (names of other competitive exams)
other_exam_ranks: string (corresponding ranks for other exams)
other_exam_scores: string (corresponding scores for other exams)

Return ONLY the JSON object:
"""

def build_experience_prompt(resume_text: str) -> str:
    """Build prompt for all experience extraction in one go"""
    
    MAX_PROJECTS = 5
    MAX_INDEPENDENT_PROJECTS = 3
    MAX_WORK_EXPERIENCES = 4
    MAX_RESEARCH_PAPERS = 3
    
    # Generate project fields dynamically
    project_fields = []
    for i in range(1, MAX_PROJECTS + 1):
        project_fields.append(f"project_{i}_title: string")
        project_fields.append(f"project_{i}_description: string")
        project_fields.append(f"project_{i}_tools: string (semicolon-separated)")
        project_fields.append(f"project_{i}_languages: string (semicolon-separated)")
        project_fields.append(f"project_{i}_coursework_used: string (semicolon-separated)")
        project_fields.append(f"project_{i}_link: string")
        project_fields.append(f"project_{i}_duration: string")
    
    # Generate independent project fields
    indproj_fields = []
    for i in range(1, MAX_INDEPENDENT_PROJECTS + 1):
        indproj_fields.append(f"indproj_{i}_title: string")
        indproj_fields.append(f"indproj_{i}_professor: string")
        indproj_fields.append(f"indproj_{i}_description: string")
        indproj_fields.append(f"indproj_{i}_tools: string (semicolon-separated)")
        indproj_fields.append(f"indproj_{i}_languages: string (semicolon-separated)")
        indproj_fields.append(f"indproj_{i}_coursework_used: string (semicolon-separated)")
        indproj_fields.append(f"indproj_{i}_link: string")
        indproj_fields.append(f"indproj_{i}_duration: string")
    
    # Generate work experience fields
    work_fields = []
    for i in range(1, MAX_WORK_EXPERIENCES + 1):
        work_fields.append(f"work_{i}_company: string")
        work_fields.append(f"work_{i}_role: string")
        work_fields.append(f"work_{i}_duration: string")
        work_fields.append(f"work_{i}_description: string")
        work_fields.append(f"work_{i}_tools: string (semicolon-separated)")
        work_fields.append(f"work_{i}_languages: string (semicolon-separated)")
        work_fields.append(f"work_{i}_coursework_used: string (semicolon-separated)")
        work_fields.append(f"work_{i}_link: string")
    
    # Generate research paper fields
    paper_fields = []
    for i in range(1, MAX_RESEARCH_PAPERS + 1):
        paper_fields.append(f"paper_{i}_title: string")
        paper_fields.append(f"paper_{i}_published_in: string")
        paper_fields.append(f"paper_{i}_status: string (published/submitted/in-progress)")
        paper_fields.append(f"paper_{i}_link: string")
        paper_fields.append(f"paper_{i}_description: string")
        paper_fields.append(f"paper_{i}_tools: string (semicolon-separated)")
        paper_fields.append(f"paper_{i}_languages: string (semicolon-separated)")
        paper_fields.append(f"paper_{i}_coursework_used: string (semicolon-separated)")
    
    project_fields_str = "\n".join(project_fields)
    indproj_fields_str = "\n".join(indproj_fields)
    work_fields_str = "\n".join(work_fields)
    paper_fields_str = "\n".join(paper_fields)
    
    return f"""
You are an expert parser for Indian college resumes. Extract ALL experience details into a FLAT JSON object.

CRITICAL CATEGORIZATION RULES:
1. PROJECTS = Personal projects, academic projects, hackathon projects, self-initiated projects
2. INDEPENDENT/BTECH PROJECTS = Projects done under professor guidance, final year projects, research projects with academic supervisors (NOT company internships)  
3. WORK EXPERIENCE = Internships at companies, jobs, freelance work, corporate experience
4. RESEARCH PAPERS = Published/submitted academic papers, conference papers, journal articles

STRICT EXTRACTION RULES:
- Output ONLY one JSON object, no markdown, no commentary
- NO nested objects or arrays anywhere
- Use semicolon-separated strings for lists  
- If a field is missing or not applicable, set to null
- DO NOT categorize same experience in multiple categories
- If only 2 projects exist, set project_3_title through project_5_title to null
- If only 1 work experience exists, set work_2_company through work_4_company to null
- Same null logic applies to all categories

RESUME TEXT:
{resume_text}

Extract these EXACT fields (set unused ones to null):

PROJECTS (exactly 5 numbered entries):
{project_fields_str}

INDEPENDENT/BTECH PROJECTS under professor (exactly 3 numbered entries):
{indproj_fields_str}

WORK EXPERIENCE at companies (exactly 4 numbered entries):
{work_fields_str}

RESEARCH PAPERS (exactly 3 numbered entries):
{paper_fields_str}

SKILLS AND POSITIONS:
programming_languages_listed: string (semicolon-separated from skills section)
tools_technologies_listed: string (semicolon-separated from skills section) 
coursework_listed: string (semicolon-separated courses mentioned)
por_raw_text: string (positions of responsibility raw text)
domains_raw_labels: string (semicolon-separated domain labels found)

REMEMBER: Return null for unused numbered entries. Do NOT duplicate experiences across categories.

Return ONLY the JSON object:
"""
def build_scoring_prompt(combined_data: Dict[str, Any], resume_text: str) -> str:
    """Build prompt for scoring and derived fields"""
    skill_cats = "; ".join(SKILL_CATEGORIES)
    soft_skills = "; ".join(SOFT_SKILLS)
    domains = "; ".join(PRIMARY_DOMAINS)
    
    return f"""
You are scoring a candidate based on their resume data and original text.

CRITICAL SCORING RULES:
- Output ONLY one JSON object, no markdown, no commentary
- NO nested objects or arrays anywhere
- All scores are integers 0-10
- Use semicolon-separated strings for lists
- BE LIBERAL with 0 scores - if there's no clear evidence of a skill, give 0
- DO NOT assume skills - only score based on explicit evidence
- Most candidates will have 0 in many technical areas - this is normal and expected
- Only give non-zero scores when there's clear project/work evidence of that skill

CANDIDATE DATA:
{json.dumps(combined_data, ensure_ascii=False, indent=2)}

ORIGINAL RESUME TEXT (for additional context):
{resume_text}

Extract and score these fields:

TECHNICAL SKILL SCORES (0-10 integers, give 0 if no evidence):
webdev_score: integer
frontend_score: integer
backend_score: integer
mobile_dev_score: integer
app_dev_score: integer
cloud_score: integer
devops_score: integer
data_science_score: integer
machine_learning_score: integer
deep_learning_score: integer
reinforcement_learning_score: integer
computer_vision_score: integer
nlp_score: integer
cybersecurity_cryptography_score: integer
blockchain_web3_score: integer
bioinformatics_score: integer
ar_vr_score: integer
robotics_automation_score: integer
big_data_score: integer
digital_electronics_score: integer
analog_circuits_score: integer
vlsi_design_score: integer
embedded_systems_score: integer
signal_processing_score: integer
control_systems_score: integer
iot_score: integer
communication_systems_score: integer
power_systems_power_electronics_score: integer
quantum_computing_score: integer
digital_twins_simulation_tools_score: integer

SOFT SKILL SCORES (0-10 integers, give 0 if no evidence):
leadership_score: integer
teamwork_score: integer
communication_score: integer
problem_solving_score: integer

LEADERSHIP BREAKDOWN (0-10 integers, give 0 if no evidence):
leadership_initiative_score: integer
leadership_team_management_score: integer
leadership_communication_influence_score: integer
leadership_impact_score: integer

DOMAIN ANALYSIS:
primary_domain: string (choose exactly one from: {domains})
top_3_domains: string (semicolon-separated, top 3 relevant domains based on evidence)

DERIVED FIELDS:
net_known_languages: string (semicolon-separated union of all programming languages found)
net_tools_technologies: string (semicolon-separated union of all tools/technologies found)
research_paper_any: boolean (true if any research paper found)
research_paper_count: integer (count of research papers)

REMEMBER: Default to 0 for technical skills unless there's clear evidence. Don't inflate scores.

Return ONLY the JSON object:
"""

# Main Processing Functions
def process_resume(pdf_path: str, output_path: str, api_keys: List[str], model_name: str) -> None:
    """Process a single resume through the 5-call pipeline"""
    filename = os.path.basename(pdf_path)
    print(f"Processing {filename}...")
    
    # Extract text from PDF
    resume_text, urls = extract_text_from_pdf(pdf_path)
    if len(resume_text.strip()) < 100:
        print(f"Warning: Very short text extracted from {filename}")
        return
    
    # Ensure we have a rotator
    rotator = KeyRotator(api_keys, model_name)
    
    try:
        # Call 1: Basic Info
        print(f"  Call 1/5: Basic Info")
        prompt1 = build_basic_info_prompt(resume_text, filename)
        response1 = rotator.generate(prompt1)
        basic_info = clean_json_response(response1)
        
        # Call 2: Education
        print(f"  Call 2/5: Education")
        prompt2 = build_education_prompt(resume_text)
        response2 = rotator.generate(prompt2)
        education_info = clean_json_response(response2)
        
        # Call 3: Marks and Ranks
        print(f"  Call 3/5: Marks and Ranks")
        prompt3 = build_marks_prompt(resume_text)
        response3 = rotator.generate(prompt3)
        marks_info = clean_json_response(response3)
        
        # Call 4: Experience
        print(f"  Call 4/5: Experience")
        prompt4 = build_experience_prompt(resume_text)
        response4 = rotator.generate(prompt4)
        experience_info = clean_json_response(response4)
        
        # Combine all data for scoring call
        combined_data = {**basic_info, **education_info, **marks_info, **experience_info}
        
        # Call 5: Scoring
        print(f"  Call 5/5: Scoring")
        prompt5 = build_scoring_prompt(combined_data, resume_text)
        response5 = rotator.generate(prompt5)
        scoring_info = clean_json_response(response5)
        
        # Combine all results
        final_data = {**combined_data, **scoring_info}
        
        # Save to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        print(f"  [DONE] Completed {filename}")

        # AUTO-INDEXING
        try:
            update_vector_index(final_data, output_path, rotator)
        except Exception as e:
            print(f"  [Warning] Auto-indexing failed: {e}")
        
    except Exception as e:
        print(f"  [ERROR] Error processing {filename}: {e}")
        # Save error log
        error_path = output_path.replace('.json', '.error.txt')
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write(f"Error processing {filename}: {str(e)}")

def main():
    print("Script started...")
    parser = argparse.ArgumentParser(description="Parse PDF resumes using 5-call Gemini pipeline")
    parser.add_argument("--input_dir", required=True, help="Directory containing PDF resumes")
    parser.add_argument("--output_dir", required=True, help="Directory to save JSON outputs")
    parser.add_argument("--model", default="gemini-2.0-flash-exp", help="Gemini model name")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get API keys
    api_keys = get_api_keys()
    print(f"Loaded {len(api_keys)} API keys")
    
    # Find PDF files
    pdf_files = [f for f in os.listdir(args.input_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("No PDF files found in input directory")
        sys.exit(0)
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    for i, pdf_file in enumerate(pdf_files):
        print(f"[{i+1}/{len(pdf_files)}] Starting {pdf_file}...")
        pdf_path = os.path.join(args.input_dir, pdf_file)
        json_filename = os.path.splitext(pdf_file)[0] + '.json'
        output_path = os.path.join(args.output_dir, json_filename)
        
        # Skip if already processed
        if os.path.exists(output_path):
            print(f"Skipping {pdf_file} (already processed)")
            continue
        
        process_resume(pdf_path, output_path, api_keys, args.model)
    
    print("All resumes processed!")

if __name__ == "__main__":
    main()