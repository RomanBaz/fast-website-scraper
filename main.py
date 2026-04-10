from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException

from scraper.crawler import crawl
from scraper.models import (
    CrawlJob,
    CrawlRequest,
    CrawlResponse,
    CrawlResultResponse,
    CrawlStatus,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Fast Website Scraper", version="1.0.0")

jobs: dict[str, CrawlJob] = {}


@app.post("/crawl", response_model=CrawlResponse, status_code=202)
async def start_crawl(request: CrawlRequest):
    """Start a new crawl job. Returns immediately with a job ID."""
    job = CrawlJob(url=str(request.url), max_pages=request.max_pages)
    jobs[job.job_id] = job

    asyncio.create_task(
        crawl(
            job,
            max_concurrency=request.max_concurrency,
            delay=request.delay,
            respect_robots=request.respect_robots,
            exclude_paths=request.exclude_paths,
            include_paths=request.include_paths,
        )
    )

    return CrawlResponse(
        job_id=job.job_id,
        status=job.status,
        url=job.url,
        pages_crawled=job.pages_crawled,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@app.get("/crawl/{job_id}", response_model=CrawlResponse)
async def get_crawl_status(job_id: str):
    """Check the status of a crawl job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return CrawlResponse(
        job_id=job.job_id,
        status=job.status,
        url=job.url,
        pages_crawled=job.pages_crawled,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
    )


@app.get("/crawl/{job_id}/results", response_model=CrawlResultResponse)
async def get_crawl_results(job_id: str):
    """Get full results of a completed crawl job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == CrawlStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Crawl still running — check back later")
    return CrawlResultResponse(
        job_id=job.job_id,
        status=job.status,
        url=job.url,
        pages_crawled=job.pages_crawled,
        pages=job.pages,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@app.delete("/crawl/{job_id}")
async def delete_crawl_job(job_id: str):
    """Delete a crawl job and its results."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    del jobs[job_id]
    return {"detail": "Job deleted"}


@app.get("/jobs", response_model=list[CrawlResponse])
async def list_jobs():
    """List all crawl jobs."""
    return [
        CrawlResponse(
            job_id=j.job_id,
            status=j.status,
            url=j.url,
            pages_crawled=j.pages_crawled,
            started_at=j.started_at,
            finished_at=j.finished_at,
            error=j.error,
        )
        for j in jobs.values()
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
