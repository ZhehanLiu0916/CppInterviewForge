# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CppInterviewForge is a C++ interview preparation agent for Chinese university students. It has two core features:
1. **Single question answering** (`/ask`) — RAG-based answer with knowledge base retrieval, web search fallback, and dual validation
2. **Interview review** (`/review`) — transcribes interview recording text, extracts questions/answers, generates reference answers, evaluates responses across 5 dimensions, and produces a structured report

Built with FastAPI + LangGraph + Chroma vector DB + LangChain. All user-facing text and prompts are in Chinese.

## Commands

```bash
# Run the API server
cd /home/admin001/CppInterviewForge
source CIFenv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Seed/rebuild the knowledge base (must be done before first run and after adding files to books/)
python scripts/seed_knowledge.py --rebuild
python scripts/seed_knowledge.py --incremental

# Run tests (requires running server)
pytest tests/test_basic.py
pytest tests/test_integration.py
pytest tests/test_exceptions.py
pytest tests/test_perf.py

# Docker
docker-compose up --build
```

## Architecture

### Two LangGraph State Machines

**QuestionGraph** (`app/graphs/question/graph.py`):
`rewrite → retrieve → [validate | web_search] → generate → format`
- Conditional edge after `retrieve`: if `max_similarity >= 0.8` → `validate`, else → `web_search`
- `validate` always goes to `generate` (whether validation passes or fails, state determines content source)
- State: `QuestionState` in `app/models/state.py`

**ReviewGraph** (`app/graphs/review/graph.py`):
`preprocess → extract_questions → (parallel: extract_answers + answer each question via QuestionGraph) → evaluate → generate_report`
- Reuses QuestionGraph for per-question answering
- State: `ReviewState` in `app/models/state.py`

### Key Directory Layout

- `app/nodes/` — LangGraph node functions (each file = one node: rewrite, retrieve, validate, generate, format, preprocess, extract_questions, extract_answers, evaluate, generate_report, web_search)
- `app/services/` — Business logic: `retriever.py` (Chroma RAG), `llm.py` (ChatOpenAI factory), `web_search.py` (Tavily/SearXNG), `chunker.py` (Markdown heading-based splitting), `document_loader.py` (MarkItDown conversion), `classifier.py` (LLM-based chunk categorization), `cache.py` (LRU cache)
- `app/core/` — `config.py` (pydantic-settings from env vars), `prompts.py` (all LLM prompt templates), `logging.py` (loguru + FastAPI intercept)
- `app/models/` — Pydantic request/response schemas and LangGraph state TypedDicts
- `app/api/routes.py` — FastAPI endpoints: POST `/api/v1/ask`, POST `/api/v1/review`, GET `/api/v1/health`
- `books/` — Knowledge base source documents (recursively scanned, supports .md/.pdf/.docx/.pptx/.txt/.html/.epub)
- `data/chroma/` — Persisted Chroma vector database
- `scripts/seed_knowledge.py` — Knowledge base ETL pipeline: scan → convert → chunk → classify → embed → store

### Configuration

All config via `.env` file (see `spec.md` Appendix A for full template). Key variables:
- `LLM_API_KEY`, `LLM_MODEL_NAME`, `LLM_BASE_URL` — LLM provider (uses SiliconFlow/硅基流动 API by default)
- `TAVILY_API_KEY` — Online search API key
- `CHROMA_PERSIST_DIR` — Chroma DB path (default `./data/chroma`)
- `BOOK_DIR` — Knowledge base documents directory (default `./book`)
- `RETRIEVAL_THRESHOLD` — Similarity threshold for KB vs web search branching (default 0.8)
- `SEARCH_ENGINE` — `tavily` or `searxng`

### Error Code System

Defined in `spec.md`: 1001-1004 (input errors), 2001-2003 (LLM errors), 3001-3002 (infrastructure errors), 9999 (unknown). Routes in `app/api/routes.py` map exceptions to these codes.

## Development Notes

- The LLM is accessed through `langchain_openai.ChatOpenAI` with a custom `base_url`, so any OpenAI-compatible API works (DeepSeek, Qwen, etc.)
- `get_llm()`, `get_validator_llm()`, `get_search_llm()` in `app/services/llm.py` provide LLM instances with different temperature/token settings for different purposes
- Chunk splitting is heading-based (`split_by_headings` in `chunker.py`), not fixed-size — chunks respect `##`/`###` boundaries with 50-800 token limits
- The QuestionGraph is compiled as a singleton (`_question_app`) via `_get_question_app()`
- Tests are HTTP-level integration tests against a running server (not unit tests)
