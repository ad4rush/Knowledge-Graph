# ─── Stage 1: Build React frontend ───────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY resume_parser.py resume_indexer.py resume_search.py merge_manual.py ./

# Copy data assets
COPY output/ ./output/
COPY manual_text/ ./manual_text/
COPY linkedin_pdfs/ ./linkedin_pdfs/
COPY Resumes/ ./Resumes/
COPY photos/ ./photos/

# Copy FAISS index and metadata
COPY resume_index.faiss resume_metadata.json ./

# Copy env
COPY .env ./

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
