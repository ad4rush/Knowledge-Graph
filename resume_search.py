import argparse
import json
import os
import faiss
import numpy as np
import google.generativeai as genai

# Configuration
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE  = os.path.join(BASE_DIR, "resume_index.faiss")
META_FILE   = os.path.join(BASE_DIR, "resume_metadata.json")
EMBED_MODEL = "models/gemini-embedding-001"
LLM_MODEL   = "gemini-2.5-flash"  # Used for final re-ranking and reasoning

# We will use all API keys to handle quota issues
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

class KeyRotator:
    def __init__(self, keys):
        self.keys = keys
        self.idx  = 10  # start a bit further in

    def call_api(self, func, *args, **kwargs):
        tried = 0
        last_error = None
        while tried < len(self.keys):
            key = self.keys[self.idx % len(self.keys)]
            self.idx += 1
            tried    += 1
            try:
                genai.configure(api_key=key)
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if "429" in err or "quota" in err or "rate" in err or "exhausted" in err or "expired" in err or "not found" in err:
                    continue
        raise RuntimeError(f"All keys failed. Last error: {last_error}")

rotator = KeyRotator(API_KEYS)


def get_embedding(text: str) -> np.ndarray:
    """Get embedding vector for the search query."""
    def _embed():
        return genai.embed_content(
            model=EMBED_MODEL,
            content=text,
            task_type="RETRIEVAL_QUERY",
        )
    result = rotator.call_api(_embed)
    vec = np.array(result["embedding"], dtype="float32")
    # L2 normalize
    vec /= np.linalg.norm(vec) + 1e-10
    return vec.reshape(1, -1)


def rerank_with_llm(query: str, candidates: list) -> str:
    """
    Passes the top candidates to Gemini LLM to re-rank and explain.
    Returns the final markdown table or response.
    """
    # Build prompt context
    context = ""
    for idx, c in enumerate(candidates):
        # We pass the distilled text so the LLM can see exactly what matched
        context += f"--- CANDIDATE {idx+1}: {c['name']} ---\n"
        context += f"Profile Info:\n{c['distilled']}\n\n"

    prompt = f"""
You are an expert technical recruiter analyzing a list of candidates returned by a semantic search engine.
The user's query is: "{query}"

I am providing you with the top {len(candidates)} candidates that matched the query based on vector similarity.
Your job is to read their profiles, RE-RANK them strictly based on how well they actually fit the user's query, and pick the best ones.

Here are the candidates:
{context}

Please provide a final ranked list of the best fits. For each candidate, provide:
1. Rank number
2. Candidate Name
3. A 1-2 sentence specific reason explaining WHY they are a good fit for this query, referencing their actual projects/skills.

Format the output cleanly. Do not hallucinate skills they don't have. If a candidate is a weak fit despite being in the list, you can skip them or mention they are a partial fit.
"""
    def _generate():
        model = genai.GenerativeModel(LLM_MODEL)
        return model.generate_content(prompt)
    
    response = rotator.call_api(_generate)
    return response.text


def main():
    parser = argparse.ArgumentParser(description="Semantic Search for Resumes")
    parser.add_argument("query", type=str, help="Natural language search query")
    parser.add_argument("--top", type=int, default=5, help="Number of candidates to fetch from FAISS before re-ranking")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM re-ranking, just show raw FAISS results")
    args = parser.parse_args()

    # Load FAISS and metadata
    if not os.path.exists(INDEX_FILE) or not os.path.exists(META_FILE):
        print("Error: Index not found. Please run resume_indexer.py first.")
        return

    print("Loading index...")
    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    print(f"Embedding query: '{args.query}'...")
    try:
        q_vec = get_embedding(args.query)
    except Exception as e:
        print(f"Error embedding query: {e}")
        return

    print("Searching vector space...")
    # Fetch extra from FAISS to account for deduplication
    k = min(args.top * 3, len(metadata))
    distances, indices = index.search(q_vec, k)

    # Fetch top candidates, deduplicating by name
    top_candidates = []
    seen_names = set()
    for i, dist in zip(indices[0], distances[0]):
        if i == -1: continue
        c = metadata[i].copy()
        name = c.get("name", "")
        if name in seen_names:
            continue
        seen_names.add(name)
        c["score"] = float(dist)
        top_candidates.append(c)
        if len(top_candidates) >= args.top:
            break

    if args.skip_llm:
        print(f"\n=== Top {len(top_candidates)} Raw Vector Matches ===\n")
        for idx, c in enumerate(top_candidates):
            print(f"{idx+1}. {c['name']} (Score: {c['score']:.3f})")
            print(f"   Domain: {c.get('primary_domain', 'N/A')}")
            print(f"   Tools : {c['distilled'][:100]}...")
            print()
        return

    print(f"Passing top {len(top_candidates)} matches to Gemini LLM for reasoning and re-ranking...\n")
    try:
        result = rerank_with_llm(args.query, top_candidates)
        print("="*60)
        print("FINAL RESULTS:")
        print("="*60)
        print(result)
        print("\n" + "="*60)
    except Exception as e:
        print(f"Error during LLM re-ranking: {e}")


if __name__ == "__main__":
    main()
