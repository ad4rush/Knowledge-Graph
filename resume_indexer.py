#!/usr/bin/env python3
"""
Resume Indexer — Build FAISS vector index from parsed resume JSONs.
Handles both output/ (rich flat schema) and manual_text/ (LinkedIn schema).
Run once. Saves resume_index.faiss + resume_metadata.json.
"""

import os, json, glob, re, time
import numpy as np
import faiss
import google.generativeai as genai

# ─── ALL API KEYS ─────────────────────────────────────────────────────────────
API_KEYS = [
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
    "AIzaSyDUgSx7V-wHs-z4v7v5bGE12JtvhhIdssI",
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

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
MANUAL_DIR  = os.path.join(BASE_DIR, "manual_text")
INDEX_FILE  = os.path.join(BASE_DIR, "resume_index.faiss")
META_FILE   = os.path.join(BASE_DIR, "resume_metadata.json")
EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIM   = 3072

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

# ─── KEY ROTATOR ──────────────────────────────────────────────────────────────
class KeyRotator:
    def __init__(self, keys):
        self.keys = keys
        self.idx  = 0

    def embed(self, text: str, retries: int = None) -> list:
        """Rotate keys automatically on 429 / quota errors. Shows real errors."""
        max_tries = retries if retries is not None else len(self.keys)
        tried = 0
        last_error = None
        while tried < max_tries:
            key = self.keys[self.idx % len(self.keys)]
            self.idx += 1
            tried    += 1
            try:
                genai.configure(api_key=key)
                result = genai.embed_content(
                    model=EMBED_MODEL,
                    content=text,
                    task_type="RETRIEVAL_DOCUMENT",
                )
                return result["embedding"]
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if tried <= 3:  # show first few errors so we know what's wrong
                    print(f"    [key {tried}] Error: {e}")
                if "429" in err or "quota" in err or "rate" in err or "exhausted" in err:
                    continue   # rate limit -> try next key immediately
                else:
                    time.sleep(0.5)  # other error -> tiny wait, try next key
        raise RuntimeError(f"All {max_tries} key attempts failed. Last error: {last_error}")


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

def test_first_key():
    """Smoke-test: try embedding a short string with any working key."""
    print("Testing API keys...")
    for idx, key in enumerate(API_KEYS):
        try:
            genai.configure(api_key=key)
            result = genai.embed_content(
                model=EMBED_MODEL,
                content="test embedding",
                task_type="RETRIEVAL_DOCUMENT",
            )
            dim = len(result["embedding"])
            print(f"  OK — key #{idx+1} works, embedding dim = {dim}")
            return True
        except Exception as e:
            if idx < 3:
                print(f"  Key #{idx+1} failed: {str(e)[:80]}")
    print("  FAIL — no working keys found")
    return False


def main():
    if not test_first_key():
        print("Aborting — fix API key issue first.")
        return

    rotator = KeyRotator(API_KEYS)

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
    indexed_names = {m["name"] for m in metadata}

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

        # Deduplicate: skip if this student name is already indexed
        if name in indexed_names:
            print(f"  [DUPE] {name} — already indexed, skipping {rel}")
            skipped_dupes += 1
            continue
        indexed_names.add(name)

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
