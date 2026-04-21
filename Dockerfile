# ── Stage 1: Build Frontend ──────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python Runtime ──────────────────────────
FROM python:3.10-slim
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy project files
COPY backend/ ./backend/
COPY resume_parser.py resume_indexer.py resume_search.py generate_graph.py ./
COPY output/ ./output/
COPY manual_text/ ./manual_text/
COPY photos/ ./photos/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create dirs for uploads
RUN mkdir -p linkedin_pdfs

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
