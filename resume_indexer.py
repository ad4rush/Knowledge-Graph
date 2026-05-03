#!/usr/bin/env python3
"""
Resume Indexer — Build FAISS vector index from parsed resume JSONs.
Handles both output/ (rich flat schema) and manual_text/ (LinkedIn schema).
Run once. Saves resume_index.faiss + resume_metadata.json.
Uses AWS Bedrock (Amazon Titan V2) for embeddings.
"""

import os, json, glob, re, time
import numpy as np
import faiss
import boto3
from dotenv import load_dotenv

load_dotenv()

# ─── AWS BEDROCK CONFIG ──────────────────────────────────────────────────────
AWS_REGION     = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBED_DIM      = 1024

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION,
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
MANUAL_DIR  = os.path.join(BASE_DIR, "manual_text")
INDEX_FILE  = os.path.join(BASE_DIR, "resume_index.faiss")
META_FILE   = os.path.join(BASE_DIR, "resume_metadata.json")

SKILL_CATS = [
    "webdev","frontend","backend","mobile_dev","app_dev","cloud","devops",
    "data_science","machine_learning","deep_learning","reinforcement_learning",
    "computer_vision","nlp","cybersecurity_cryptography","blockchain_web3",
    "bioinformatics","ar_vr","robotics_automation","big_data",
    "digital_electronics","analog_circuits","vlsi_design","embedded_systems",
    "signal_processing","control_systems","iot","communication_systems",
    "power_systems_power_electronics","quantum_computing",
    "digital_twins_simulation_tools",
]

# ─── EMBEDDING HELPER ────────────────────────────────────────────────────────
class KeyRotator:
    """Bedrock embedding wrapper with retry logic."""
    def __init__(self):
        self.client = bedrock_runtime

    def embed(self, text: str, retries: int = 3) -> list:
        """Generate embedding using Amazon Titan V2 with retries."""
        last_error = None
        for attempt in range(retries):
            try:
                payload = {
                    "inputText": text[:8000],
                    "dimensions": EMBED_DIM,
                    "normalize": True,
                }
                response = self.client.invoke_model(
                    body=json.dumps(payload),
                    modelId=EMBED_MODEL_ID,
                    accept="application/json",
                    contentType="application/json",
                )
                result = json.loads(response["body"].read())
                return result["embedding"]
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if attempt < 2:
                    print(f"    [Attempt {attempt+1}] Error: {e}")
                if "throttl" in err or "rate" in err:
                    time.sleep(2 * (attempt + 1))
                else:
                    time.sleep(0.5)
        raise RuntimeError(f"Embedding failed after {retries} attempts. Last error: {last_error}")


# ─── DISTILLERS ───────────────────────────────────────────────────────────────

def _clean(s):
    """Strip LinkedIn noise and excessive whitespace."""
    if not s:
        return ""
    s = re.sub(r"Show project|Show all \d+ details|Other contributors|View all contributors|Show publication", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def distill_output_schema(d: dict) -> str:
    """Distill a rich flat JSON (output/ folder) to a token-efficient text blob."""
    parts = []

    # Identity
    parts.append(f"Name: {d.get('name','')}")
    parts.append(f"Branch: {d.get('branch','')} | College: {d.get('current_college_name','')} | CGPA: {d.get('current_college_cgpa','')}")
    parts.append(f"Primary domain: {d.get('primary_domain','')} | Top domains: {d.get('top_3_domains','')}")

    # Non-zero skill scores as readable text
    scores = [f"{c.replace('_',' ')}:{d.get(c+'_score',0) or 0}"
              for c in SKILL_CATS if (d.get(c+"_score") or 0) > 0]
    if scores:
        parts.append("Skill scores: " + ", ".join(scores))

    # Languages & tools
    if d.get("net_known_languages"):
        parts.append("Languages: " + str(d["net_known_languages"]))
    if d.get("net_tools_technologies"):
        parts.append("Tools: " + str(d["net_tools_technologies"]))
    if d.get("relevant_coursework"):
        parts.append("Courses: " + str(d["relevant_coursework"]))
    if d.get("certifications_list"):
        parts.append("Certifications: " + str(d["certifications_list"]))

    # Projects (title + first 220 chars of description)
    for i in range(1, 9):
        title = d.get(f"project_{i}_title")
        if not title:
            break
        desc  = (d.get(f"project_{i}_description") or "")[:220]
        tools = d.get(f"project_{i}_tools") or ""
        parts.append(f"Project: {title}. {desc} [{tools}]")

    # Independent / BTP projects
    for i in range(1, 6):
        title = d.get(f"indproj_{i}_title")
        if not title:
            break
        desc  = (d.get(f"indproj_{i}_description") or "")[:180]
        tools = d.get(f"indproj_{i}_tools") or ""
        prof  = d.get(f"indproj_{i}_professor") or ""
        parts.append(f"Research project (under {prof}): {title}. {desc} [{tools}]")

    # Work experience
    for i in range(1, 9):
        company = d.get(f"work_{i}_company")
        if not company:
            break
        role  = d.get(f"work_{i}_role") or ""
        desc  = (d.get(f"work_{i}_description") or "")[:220]
        tools = d.get(f"work_{i}_tools") or ""
        parts.append(f"Work: {role} at {company}. {desc} [{tools}]")

    # Research papers
    for i in range(1, 7):
        title = d.get(f"paper_{i}_title")
        if not title:
            break
        venue = d.get(f"paper_{i}_published_in") or ""
        parts.append(f"Paper: {title} [{venue}]")

    # Soft info
    if d.get("awards_list"):
        parts.append("Awards: " + str(d["awards_list"])[:300])
    if d.get("por_positions_list"):
        parts.append("POR: " + str(d["por_positions_list"])[:250])

    # Join, drop None/null lines
    text = "\n".join(p for p in parts if p and "None" not in p and ": " not in p or any(c.isalpha() for c in p.split(":",1)[-1]))
    return text.strip()


def distill_manual_schema(d: dict) -> str:
    """Distill a LinkedIn-export JSON (manual_text/ folder) to a text blob."""
    parts = []

    parts.append(f"Name: {d.get('student_name','')}")

    skills_raw = _clean(d.get("skills") or "")
    if skills_raw:
        parts.append("Skills: " + skills_raw[:600])

    courses_raw = _clean(d.get("courses") or "")
    if courses_raw:
        parts.append("Courses: " + courses_raw[:350])

    other_raw = _clean(d.get("other_info") or "")
    if other_raw:
        parts.append("Other info: " + other_raw[:500])

    # Projects
    proj_data = d.get("projects") or {}
    proj_raw = ""
    if isinstance(proj_data, dict):
        proj_raw = _clean(proj_data.get("raw_text") or "")
    elif isinstance(proj_data, str):
        proj_raw = _clean(proj_data)

    if proj_raw:
        parts.append("Projects: " + proj_raw[:700])

    return "\n".join(p for p in parts if p).strip()


def distill(filepath: str) -> tuple:
    """
    Returns (name, source_schema, distilled_text, raw_dict).
    source_schema is 'output' or 'manual'.
    """
    with open(filepath, encoding="utf-8") as f:
        d = json.load(f)

    if "name" in d and any(k.endswith("_score") for k in d):
        # Rich flat schema (output/)
        text   = distill_output_schema(d)
        name   = d.get("name", os.path.basename(filepath))
        schema = "output"
    else:
        # LinkedIn manual schema (manual_text/)
        text   = distill_manual_schema(d)
        name   = d.get("student_name", os.path.basename(filepath))
        schema = "manual"

    return name, schema, text, d


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def test_bedrock_connection():
    """Smoke-test: try embedding a short string via Bedrock."""
    print("Testing AWS Bedrock connection...")
    try:
        payload = {
            "inputText": "test embedding",
            "dimensions": EMBED_DIM,
            "normalize": True,
        }
        response = bedrock_runtime.invoke_model(
            body=json.dumps(payload),
            modelId=EMBED_MODEL_ID,
            accept="application/json",
            contentType="application/json",
        )
        result = json.loads(response["body"].read())
        dim = len(result["embedding"])
        print(f"  OK — Bedrock Titan V2 works, embedding dim = {dim}")
        return True
    except Exception as e:
        print(f"  FAIL — Bedrock error: {e}")
        return False


def main():
    if not test_bedrock_connection():
        print("Aborting — fix AWS credentials or Bedrock access first.")
        return

    rotator = KeyRotator()

    # Collect all JSON files from both folders
    # Output/ files come first so they take priority during dedup
    files = (
        glob.glob(os.path.join(OUTPUT_DIR,  "*.json")) +
        glob.glob(os.path.join(MANUAL_DIR,  "*.json"))
    )
    print(f"Found {len(files)} JSON files total.\n")

    # Load existing metadata so we can resume if interrupted
    if os.path.exists(META_FILE):
        with open(META_FILE, encoding="utf-8") as f:
            metadata = json.load(f)
        already_done = {m["source_file"] for m in metadata}
        print(f"  Already indexed: {len(already_done)} candidates — skipping them.\n")
    else:
        metadata       = []
        already_done   = set()

    # Load existing FAISS index or create new one
    if os.path.exists(INDEX_FILE) and metadata:
        index = faiss.read_index(INDEX_FILE)
    else:
        index = faiss.IndexFlatIP(EMBED_DIM)   # Inner-product (cosine after norm)

    # Track names already indexed to prevent duplicates
    # (output/ files listed first, so they win over manual_text/ dupes)
    indexed_names = {m["name"].lower().strip() for m in metadata if m.get("name")}

    new_count = 0
    skipped_dupes = 0
    for filepath in files:
        rel = os.path.relpath(filepath, BASE_DIR)
        if rel in already_done:
            continue

        try:
            name, schema, text, raw = distill(filepath)
        except Exception as e:
            print(f"  [SKIP] {rel} — distill error: {e}")
            continue

        if not name:
            continue

        normalized_name = name.lower().strip()
        # Deduplicate: skip if this student name is already indexed
        if normalized_name in indexed_names:
            print(f"  [DUPE] {name} — already indexed, skipping {rel}")
            skipped_dupes += 1
            continue
        indexed_names.add(normalized_name)

        if len(text.strip()) < 30:
            print(f"  [WARN] {name} — almost empty profile, flagging.")
            text = f"Name: {name}. Incomplete profile."

        token_est = len(text) // 4
        print(f"  Embedding: {name:<35} schema={schema}  ~{token_est} tokens")

        try:
            vector = rotator.embed(text)
        except RuntimeError as e:
            print(f"  [FAIL] {name} — {e}")
            # Save progress so far and exit gracefully
            break

        # L2-normalise so IndexFlatIP == cosine similarity
        vec_np = np.array(vector, dtype="float32")
        vec_np /= np.linalg.norm(vec_np) + 1e-10
        index.add(vec_np.reshape(1, -1))

        metadata.append({
            "index":        index.ntotal - 1,
            "name":         name,
            "schema":       schema,
            "source_file":  rel,
            "token_est":    token_est,
            "distilled":    text,           # stored for LLM re-ranking later
            # quick-access fields for display
            "branch":       raw.get("branch") or raw.get("student_name",""),
            "cgpa":         raw.get("current_college_cgpa"),
            "primary_domain": raw.get("primary_domain", ""),
            "top_domains":  raw.get("top_3_domains", ""),
        })

        new_count += 1

    # Save index and metadata
    faiss.write_index(index, INDEX_FILE)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Indexed {new_count} new + {len(already_done)} existing = {index.ntotal} total candidates.")
    if skipped_dupes:
        print(f"   Skipped {skipped_dupes} duplicate entries (same student in both output/ and manual_text/).")
    print(f"   FAISS index -> {INDEX_FILE}")
    print(f"   Metadata    -> {META_FILE}")


if __name__ == "__main__":
    main()
