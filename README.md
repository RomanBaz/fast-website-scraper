# Fast Website Scraper

Async website crawler with a REST API. Crawls all pages of a given domain, extracts text content, and returns structured JSON results.

## Features

- **Fast async crawling** with configurable concurrency (up to 50 parallel requests)
- **REST API** powered by FastAPI with auto-generated Swagger docs
- **API key authentication** — Bearer token auth on all endpoints
- **URL filtering** — exclude or include pages by glob patterns
- **Respects robots.txt** by default
- **Rate limiting** — configurable delay between requests
- **Same-domain only** — stays within the target website

## Quick Start

```bash
pip install -r requirements.txt
API_KEY=your-secret-key python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/docs`

## Authentication

All endpoints require a Bearer token via the `API_KEY` environment variable.

```bash
curl -H "Authorization: Bearer your-secret-key" http://localhost:8000/jobs
```

| Scenario | Response |
|----------|----------|
| No token | `403 Not authenticated` |
| Wrong token | `401 Invalid API key` |
| `API_KEY` not set on server | `500 API_KEY not configured` |

## API

All examples below include the required auth header.

### Start a crawl

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Authorization: Bearer your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 100,
    "max_concurrency": 10,
    "delay": 0.2,
    "respect_robots": true,
    "exclude_paths": ["/blog*", "/tag/*"],
    "include_paths": []
  }'
```

Response (`202`):
```json
{
  "job_id": "abc123",
  "status": "pending",
  "url": "https://example.com/",
  "pages_crawled": 0
}
```

### Check status

```bash
curl -H "Authorization: Bearer your-secret-key" \
  http://localhost:8000/crawl/{job_id}
```

### Get results

```bash
curl -H "Authorization: Bearer your-secret-key" \
  http://localhost:8000/crawl/{job_id}/results
```

Response:
```json
{
  "job_id": "abc123",
  "status": "completed",
  "pages_crawled": 25,
  "pages": [
    {
      "url": "https://example.com/about",
      "title": "About Us",
      "text": "Extracted page text...",
      "links": ["https://example.com/contact"],
      "crawled_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### List all jobs

```bash
curl -H "Authorization: Bearer your-secret-key" \
  http://localhost:8000/jobs
```

### Delete a job

```bash
curl -X DELETE -H "Authorization: Bearer your-secret-key" \
  http://localhost:8000/crawl/{job_id}
```

## URL Filtering

| Parameter | Type | Description |
|-----------|------|-------------|
| `exclude_paths` | `string[]` | Glob patterns to skip. E.g. `["/blog*", "/tag/*"]` |
| `include_paths` | `string[]` | If set, only matching URLs are crawled. E.g. `["/services/*"]` |

Patterns match against the URL path with slashes normalized.

## Configuration

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `max_pages` | 100 | 1–10,000 | Max pages to crawl |
| `max_concurrency` | 10 | 1–50 | Parallel requests |
| `delay` | 0.2s | 0–10s | Delay between requests |
| `respect_robots` | true | — | Honor robots.txt |

## Deployment (Railway)

1. Push to GitHub
2. Create a new project on [railway.app](https://railway.app) from the repo
3. Add the `API_KEY` environment variable in **Settings > Variables**
4. Railway auto-detects Python + `Procfile` and deploys

## Project Structure

```
fast-website-scraper/
├── main.py              # FastAPI application
├── Procfile             # Railway deploy config
├── requirements.txt     # Dependencies
└── scraper/
    ├── __init__.py
    ├── models.py        # Pydantic request/response models
    ├── parser.py        # HTML text & link extraction
    └── crawler.py       # Async crawler engine
```
