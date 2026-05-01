#!/usr/bin/env python3
"""
Resume -> Flat JSON (raw + scores), two Claude calls per resume, best-PDF extraction.

Usage:
  python Parser.py --input_dir /path/to/resumes --output_dir /path/to/output

Env:
  AWS_ACCESS_KEY_ID        -> AWS access key
  AWS_SECRET_ACCESS_KEY    -> AWS secret key
  AWS_DEFAULT_REGION       -> AWS region (default: ap-southeast-2)

Install:
  pip install boto3 pymupdf tqdm python-dotenv
"""

import os
import re
import sys
import json
import time
import math
import argparse
from typing import List, Dict, Any, Optional, Tuple

# 3rd-party
try:
    import fitz  # PyMuPDF
except ImportError:
    print("Missing dependency 'pymupdf'. Install with: pip install pymupdf", file=sys.stderr)
    raise

import boto3
from dotenv import load_dotenv

load_dotenv()

# AWS Bedrock config (APAC cross-region inference profiles — confirmed ACTIVE)
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
HAIKU_MODEL_ID = "apac.anthropic.claude-3-haiku-20240307-v1:0"
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

from tqdm import tqdm

# -----------------------------
# Configuration constants
# -----------------------------
MAX_PROJECTS = 8
MAX_INDEPENDENT_PROJECTS = 5
MAX_WORK_EXPERIENCES = 8
MAX_PAPERS = 6

# Categories to score (0–10 integers). Keep names flat & unambiguous.
SKILL_CATEGORIES = [
    "webdev", "frontend", "backend", "mobile_dev", "app_dev",
    "cloud", "devops", "data_science", "machine_learning",
    "deep_learning", "reinforcement_learning", "computer_vision",
    "nlp", "cybersecurity_cryptography", "blockchain_web3",
    "bioinformatics", "ar_vr", "robotics_automation", "big_data",
    "digital_electronics", "analog_circuits", "vlsi_design",
    "embedded_systems", "signal_processing", "control_systems",
    "iot", "communication_systems",
    "power_systems_power_electronics", "quantum_computing",
    "digital_twins_simulation_tools"
]

SOFT_SKILLS = ["leadership", "teamwork", "communication", "problem_solving"]

PRIMARY_DOMAIN_CHOICES = [
    "cs_general", "webdev", "frontend", "backend", "mobile_dev", "app_dev",
    "data_science", "machine_learning", "deep_learning", "nlp", "computer_vision",
    "cloud", "devops", "cybersecurity_cryptography", "blockchain_web3",
    "bioinformatics", "ar_vr", "robotics_automation", "big_data",
    "digital_electronics", "analog_circuits", "vlsi_design", "embedded_systems",
    "signal_processing", "control_systems", "iot", "communication_systems",
    "power_systems_power_electronics", "quantum_computing", "digital_twins_simulation_tools",
    "other"
]

# -----------------------------
# Helpers
# -----------------------------
def call_bedrock(prompt: str, model_id: str = None, max_tokens: int = 4096) -> str:
    """Call Claude via AWS Bedrock Converse API."""
    if model_id is None:
        model_id = HAIKU_MODEL_ID
    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.3},
    )
    return response["output"]["message"]["content"][0]["text"]

def read_pdf_with_links(pdf_path: str) -> Tuple[str, List[str]]:
    """
    Extract text and URLs from PDF using PyMuPDF.
    """
    doc = fitz.open(pdf_path)
    texts = []
    urls = []
    for page in doc:
        texts.append(page.get_text("text"))
        try:
            for lnk in page.get_links():
                uri = lnk.get("uri")
                if uri and isinstance(uri, str):
                    urls.append(uri.strip())
        except Exception:
            # Some pages may not expose links properly; ignore
            pass
    doc.close()
    text = "\n".join(texts)
    # Dedup & normalize URLs
    clean_urls = []
    seen = set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            clean_urls.append(u)
    return text, clean_urls

def extract_emails_from_text(text: str) -> List[str]:
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    return list(dict.fromkeys(re.findall(pattern, text)))

def extract_probable_addresses(text: str, max_chars: int = 400):
    """
    Naive heuristic to pick an address block (if labelled). The LLM will do the final extraction.
    """
    blocks = []
    address_keywords = ["address", "permanent address", "current address", "residential address"]
    lines = text.splitlines()
    for i, line in enumerate(lines):
        lower = line.lower().strip()
        if any(k in lower for k in address_keywords):
            # Capture this line and a few below, up to max_chars
            chunk = line
            j = i + 1
            while j < len(lines) and len(chunk) < max_chars:
                if lines[j].strip() == "":
                    break
                chunk += " " + lines[j]
                j += 1
            blocks.append(chunk.strip())
    return blocks[:3]

def coerce_json(s: str) -> Dict[str, Any]:
    """
    Try to parse model output into JSON dict robustly.
    - Extract inside ```json ... ``` if present
    - Remove trailing commas
    - Replace smart quotes
    - Ensure 'null' is lowercase
    """
    if not isinstance(s, str):
        raise ValueError("Model output not a string")
    # Extract fenced json
    fence = re.search(r"```json\s*(\{.*?\})\s*```", s, flags=re.S | re.M)
    if fence:
        s = fence.group(1)

    # Sometimes the model returns just {...} without fences
    # Clean smart quotes
    s = s.replace("“", '"').replace("”", '"').replace("’", "'")
    # Strip BOM/spurious
    s = s.strip()

    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Force lowercase null/true/false if uppercased accidentally
    s = re.sub(r"\bNULL\b", "null", s)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)

    try:
        return json.loads(s)
    except Exception as e:
        # As a last resort, try to yank the first {...} blob
        m = re.search(r"(\{.*\})", s, flags=re.S)
        if m:
            candidate = re.sub(r",\s*([}\]])", r"\1", m.group(1))
            return json.loads(candidate)
        raise ValueError(f"Failed to parse JSON: {e}\n---RAW---\n{s[:1000]}...")

def save_json(path: str, data: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def merge_flat_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        out[k] = v
    return out

def union_semicolon_lists(*vals: str) -> str:
    """
    Union of semicolon-separated strings -> dedup -> semicolon-separated (sorted).
    """
    items = []
    for v in vals:
        if not v:
            continue
        for piece in str(v).split(";"):
            piece = piece.strip()
            if piece:
                items.append(piece.lower())
    dedup = sorted(set(items))
    return "; ".join(dedup)

def compute_jee_equivalent_from_raw(raw: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """
    Deterministic fallback (done in code) to complement model's computation.
    Rules:
      - If jee_main_rank present -> use it
      - Else if jee_advanced_rank present -> round(adv * 0.8)
      - Else if neet_rank present -> round(neet * 1.5)
      - Else if marks_12_percent present -> map as below
      - Else if marks_10_percent present -> map as below
      - Else -> None
    """
    def to_int(x):
        try:
            return int(str(x).strip())
        except:
            return None

    def to_float(x):
        try:
            return float(str(x).strip())
        except:
            return None

    jm = to_int(raw.get("jee_main_rank"))
    if jm:
        return jm, "jee_main_rank"

    ja = to_int(raw.get("jee_advanced_rank"))
    if ja:
        return round(ja * 0.8), "0.8x jee_advanced_rank"

    neet = to_int(raw.get("neet_rank"))
    if neet:
        return round(neet * 1.5), "1.5x neet_rank"

    p12 = to_float(raw.get("marks_12_percent"))
    if p12 is not None:
        if p12 >= 99:   return 1000, "percentile_map_12_>=99"
        if p12 >= 98:   return 2000, "percentile_map_12_[98,99)"
        if p12 >= 95:   return 5000, "percentile_map_12_[95,98)"
        if p12 >= 90:   return 15000, "percentile_map_12_[90,95)"
        if p12 >= 85:   return 30000, "percentile_map_12_[85,90)"
        if p12 >= 80:   return 50000, "percentile_map_12_[80,85)"
        return 80000, "percentile_map_12_<80"

    p10 = to_float(raw.get("marks_10_percent"))
    if p10 is not None:
        if p10 >= 99:   return 1000, "percentile_map_10_>=99"
        if p10 >= 98:   return 2000, "percentile_map_10_[98,99)"
        if p10 >= 95:   return 5000, "percentile_map_10_[95,98)"
        if p10 >= 90:   return 15000, "percentile_map_10_[90,95)"
        if p10 >= 85:   return 30000, "percentile_map_10_[85,90)"
        if p10 >= 80:   return 50000, "percentile_map_10_[80,85)"
        return 80000, "percentile_map_10_<80"

    return None, "no_rule_applicable"

# -----------------------------
# Prompt Builders
# -----------------------------
def build_prompt_extraction(resume_text: str, urls: List[str], filename: str) -> str:
    """
    Build RAW extraction prompt (flat JSON, no nesting, enumerated).
    Lists must be semicolon-separated strings, not arrays.
    For repeated structures (projects, etc.): use project_1_title ... project_N_* upto configured maxima.
    Fill null if missing.
    """
    url_block = "; ".join(urls) if urls else ""
    # Describe the exact expected flat keys.
    header = f"""
You are an expert parser for Indian college resumes. Extract a STRICTLY FLAT JSON object.
ABSOLUTE RULES:
- Output ONLY one JSON object, no markdown, no commentary.
- NO nested objects or arrays; use semicolon-separated strings for lists.
- For repeated entities (projects, independent projects, work, papers), use enumerated fields up to given maxima.
- If a field is not present, set it to null (not "N/A").
- Dates must be ISO if possible: YYYY-MM-DD or YYYY.
- Keep decimals for CGPA.
- DO NOT invent facts. Prefer null over guessing.
- Use text and the URL list below (e.g., LinkedIn/GitHub/LeetCode may appear as clickable links).
- Resume filename: {filename}

URLS_FOUND (may help):
{url_block}

Return exactly these keys:

### Identity & Contact
name, dob, address_current, address_permanent, email, github_url, linkedin_url, leetcode_url, personal_website_url, branch, batch, resume_filename

### Current College Summary
current_college_cgpa, graduation_date_overall, in_college_currently

### Education (separate blocks, flat keys)
ug1_college_name, ug1_branch, ug1_batch, ug1_cgpa, ug1_graduation_date, ug1_status
ug2_college_name, ug2_branch, ug2_batch, ug2_cgpa, ug2_graduation_date, ug2_status
pg1_college_name, pg1_branch, pg1_batch, pg1_cgpa, pg1_graduation_date, pg1_status
pg2_college_name, pg2_branch, pg2_batch, pg2_cgpa, pg2_graduation_date, pg2_status
phd_college_name, phd_branch, phd_batch, phd_cgpa, phd_graduation_date, phd_status

### Marks & Exams
marks_10_percent, marks_12_percent, board_10, board_12, jee_main_rank, jee_advanced_rank, neet_rank, other_exam_name, other_exam_rank

### Skills / Tools / Coursework (semicolon-separated, dedup lowercase)
programming_languages_listed, tools_technologies_listed, coursework_listed
programming_languages_in_projects, tools_technologies_in_projects, coursework_used_in_projects
net_known_languages, net_tools_technologies
domains_raw_labels

### Positions of Responsibility
por_raw_text

### Projects (up to {MAX_PROJECTS})
"""  # noqa: E501

    proj_lines = []
    for i in range(1, MAX_PROJECTS + 1):
        proj_lines += [
            f"project_{i}_title, project_{i}_description, project_{i}_tools, project_{i}_languages, project_{i}_coursework_used, project_{i}_link"
        ]

    indproj_lines = []
    for i in range(1, MAX_INDEPENDENT_PROJECTS + 1):
        indproj_lines += [
            f"indproj_{i}_title, indproj_{i}_description, indproj_{i}_tools, indproj_{i}_languages, indproj_{i}_coursework_used, indproj_{i}_link"
        ]

    work_lines = []
    for i in range(1, MAX_WORK_EXPERIENCES + 1):
        work_lines += [
            f"work_{i}_company, work_{i}_role, work_{i}_duration, work_{i}_description, work_{i}_tools, work_{i}_languages, work_{i}_link"
        ]

    paper_lines = []
    for i in range(1, MAX_PAPERS + 1):
        paper_lines += [
            f"paper_{i}_title, paper_{i}_published_in, paper_{i}_status, paper_{i}_link, paper_{i}_description"
        ]

    footer = f"""
### Independent/B.Tech Projects under Professor (up to {MAX_INDEPENDENT_PROJECTS})
{os.linesep.join(indproj_lines)}

### Work Experience (Company) (up to {MAX_WORK_EXPERIENCES})
{os.linesep.join(work_lines)}

### Research Papers (up to {MAX_PAPERS})
{os.linesep.join(paper_lines)}

### All URLs (semicolon-separated)
all_urls_found

Fill `net_known_languages` as union of programming_languages_listed and programming_languages_in_projects (dedup, lowercase, semicolon-separated).
Fill `net_tools_technologies` as union of tools_technologies_listed and tools_technologies_in_projects (dedup, lowercase, semicolon-separated).

NOW, return ONLY the JSON object. Nothing else.
"""

    body = f"RESUME_TEXT:\n{resume_text}"
    return header + "\n" + body + "\n" + footer

def build_prompt_scoring(raw_json: Dict[str, Any], resume_text: str) -> str:
    """
    Build SCORING prompt. Takes the raw extraction JSON (flat) and text for context.
    Output: flat JSON with only the scoring/derived fields; no arrays.
    """
    raw_json_str = json.dumps(raw_json, ensure_ascii=False)

    categories = "; ".join(SKILL_CATEGORIES)
    softs = "; ".join(SOFT_SKILLS)
    domains = "; ".join(PRIMARY_DOMAIN_CHOICES)

    prompt = f"""
You are scoring a candidate based on their resume.
Rules:
- Output ONLY one flat JSON object (no arrays, no nested objects).
- All scores are integers 0-10.
- If insufficient evidence, use 0 (do NOT invent).
- Choose exactly one primary_domain from: {domains}.
- For top_3_domains, return a semicolon-separated string (no arrays).
- For booleans, use true/false (lowercase).
- Use both the raw JSON and resume text below.

RAW_JSON (from previous step, do not alter keys/values): {raw_json_str}

RESUME_TEXT (for evidence):
{resume_text}

Return exactly these keys:

### Domain/Skill Scores (0–10 integers)
"""  # noqa: E501

    cat_lines = []
    for cat in SKILL_CATEGORIES:
        cat_lines.append(f"{cat}_score")

    soft_lines = []
    for s in SOFT_SKILLS:
        soft_lines.append(f"{s}_score")

    tail = f"""
primary_domain
top_3_domains

### Leadership breakdown (0-10, model your best judgment from PoR and project leadership signals)
leadership_initiative_score
leadership_team_management_score
leadership_communication_influence_score
leadership_impact_score
net_leadership_score  # ceil(avg of the 4 leadership_* scores)

### Research & Papers
research_paper_any  # true/false
research_paper_primary_link

### Normalized competitiveness
jee_equivalent_rank_model
jee_equivalent_rule_model

COMPUTE jee_equivalent_rank_model using EXACTLY these fallback rules in order:
1) If jee_main_rank present -> use it.
2) Else if jee_advanced_rank present -> round(jee_advanced_rank * 0.8)
3) Else if neet_rank present -> round(neet_rank * 1.5)
4) Else if marks_12_percent present -> map:
   >=99 -> 1000; >=98 -> 2000; >=95 -> 5000; >=90 -> 15000; >=85 -> 30000; >=80 -> 50000; else -> 80000
5) Else if marks_10_percent present -> same mapping as above.
6) Else -> null
Also set jee_equivalent_rule_model to the rule identifier used.

Return ONLY the JSON object. Nothing else.
"""
    return (
        prompt
        + "\n"
        + "\n".join(cat_lines)
        + "\n"
        + "\n".join(soft_lines)
        + "\n"
        + tail
    )

# -----------------------------
# Core pipeline
# -----------------------------
def call_model_with_retry(model_name: str, api_keys, prompt: str, max_retries: int = 3, sleep_s: float = 1.5) -> str:
    """Call Claude via Bedrock with retries."""
    err = None
    for attempt in range(max_retries):
        try:
            return call_bedrock(prompt, model_id=HAIKU_MODEL_ID)
        except Exception as e:
            err = e
            time.sleep(sleep_s * (attempt + 1))
    raise RuntimeError(f"Bedrock call failed after {max_retries} attempts: {err}")

def process_one_resume(pdf_path: str, out_json_path: str, model_name: str, api_keys: List[str]) -> None:
    # Extract text + urls
    resume_text, urls = read_pdf_with_links(pdf_path)
    # Fallback: if extraction yielded extremely short text, warn (user can add OCR later if needed)
    if len(resume_text.strip()) < 200:
        print(f"WARNING: Very short text extracted from {os.path.basename(pdf_path)}; check if the PDF is scanned.", file=sys.stderr)

    # Give the model helpful context: also embed emails found directly
    emails = extract_emails_from_text(resume_text)
    if emails:
        resume_text += "\n\nEMAILS_FOUND_BY_REGEX: " + "; ".join(emails)
    addr_blocks = extract_probable_addresses(resume_text)
    if addr_blocks:
        resume_text += "\n\nPOSSIBLE_ADDRESS_BLOCKS:\n- " + "\n- ".join(addr_blocks)

    filename = os.path.basename(pdf_path)

    # ---------- Call 1: RAW extraction ----------
    prompt1 = build_prompt_extraction(resume_text=resume_text, urls=urls, filename=filename)
    raw_out_text = call_model_with_retry(model_name, api_keys, prompt1)
    raw_json = coerce_json(raw_out_text)

    # Ensure required flat helpers
    raw_json["resume_filename"] = raw_json.get("resume_filename") or filename

    # ---------- Call 2: SCORING ----------
    prompt2 = build_prompt_scoring(raw_json, resume_text)
    scoring_text = call_model_with_retry(model_name, api_keys, prompt2)
    scoring_json = coerce_json(scoring_text)

    # ---------- Post-process / merge ----------
    # Union fields we can compute deterministically too
    # (Only if raw keys exist; keep model's results too)
    computed_jee_eq, rule = compute_jee_equivalent_from_raw(raw_json)
    if computed_jee_eq is not None:
        scoring_json.setdefault("jee_equivalent_rank_model_codecheck", computed_jee_eq)
        scoring_json.setdefault("jee_equivalent_rule_model_codecheck", rule)

    # Merge flat dicts: raw first, then scoring fields overwrite/add
    merged = merge_flat_dicts(raw_json, scoring_json)

    # Write JSON
    save_json(out_json_path, merged)

def main():
    parser = argparse.ArgumentParser(description="Parse resumes (PDF) -> flat JSON (raw+scores) via AWS Bedrock (2-call pipeline).")
    parser.add_argument("--input_dir", required=True, help="Folder containing PDF resumes.")
    parser.add_argument("--output_dir", required=True, help="Folder to write JSON outputs.")
    parser.add_argument("--model", default=HAIKU_MODEL_ID,
                        help="Bedrock model ID.")
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    model_name = args.model

    if not os.path.isdir(input_dir):
        print(f"ERROR: input_dir not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    api_keys = []  # Not needed for Bedrock, kept for API compatibility

    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("No PDF files found in input_dir.")
        sys.exit(0)

    print(f"Using model: {model_name}")
    print(f"API keys loaded: {len(api_keys)}")
    print(f"Resumes found: {len(pdf_files)}")
    print(f"Output dir: {output_dir}")

    for fname in tqdm(pdf_files, desc="Processing resumes"):
        in_path = os.path.join(input_dir, fname)
        base = os.path.splitext(fname)[0]
        out_path = os.path.join(output_dir, f"{base}.json")

        if os.path.exists(out_path):
            # Skip if already parsed
            continue

        try:
            process_one_resume(in_path, out_path, model_name, api_keys)
        except Exception as e:
            # Log error and continue next file
            errlog = os.path.join(output_dir, f"{base}.error.txt")
            with open(errlog, "w", encoding="utf-8") as ef:
                ef.write(str(e))
            print(f"ERROR processing {fname}: {e}", file=sys.stderr)

    print("Done.")

if __name__ == "__main__":
    main()
