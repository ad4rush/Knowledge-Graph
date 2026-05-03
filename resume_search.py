#!/usr/bin/env python3
"""
Resume Search — Semantic search using FAISS + AWS Bedrock LLM re-ranking.
Uses Amazon Titan V2 for query embedding, Claude 3.5 Sonnet for re-ranking.
"""

import argparse
import json
import os
import faiss
import numpy as np
import boto3
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE     = os.path.join(BASE_DIR, "resume_index.faiss")
META_FILE      = os.path.join(BASE_DIR, "resume_metadata.json")
AWS_REGION     = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBED_DIM      = 1024
LLM_MODEL_ID   = "amazon.nova-micro-v1:0"  # Updated to Amazon Native model

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION,
)


def get_embedding(text: str) -> np.ndarray:
    """Get embedding vector for the search query using Titan V2."""
    payload = {
        "inputText": text[:8000],
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
    vec = np.array(result["embedding"], dtype="float32")
    # L2 normalize
    vec /= np.linalg.norm(vec) + 1e-10
    return vec.reshape(1, -1)


def rerank_with_llm(query: str, candidates: list) -> str:
    """
    Passes the top candidates to Claude via Bedrock to re-rank and explain.
    Returns the final markdown table or response.
    """
    # Build prompt context
    context = ""
    for idx, c in enumerate(candidates):
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
    response = bedrock_runtime.converse(
        modelId=LLM_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": 2048,
            "temperature": 0.3,
        },
    )
    return response["output"]["message"]["content"][0]["text"]


def main():
    parser = argparse.ArgumentParser(description="Semantic Search for Resumes (AWS Bedrock)")
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

    print(f"Passing top {len(top_candidates)} matches to Claude for reasoning and re-ranking...\n")
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
