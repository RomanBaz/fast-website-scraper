from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class CrawlStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int = Field(default=100, ge=1, le=10000)
    max_concurrency: int = Field(default=10, ge=1, le=50)
    delay: float = Field(default=0.2, ge=0, le=10, description="Delay between requests in seconds")
    respect_robots: bool = True
    exclude_paths: list[str] = Field(
        default=[],
        description="Glob patterns to exclude (matched against URL path). E.g. ['/blog*', '/tag/*']",
    )
    include_paths: list[str] = Field(
        default=[],
        description="If set, only URLs matching these glob patterns are crawled. E.g. ['/services/*']",
    )


class PageResult(BaseModel):
    url: str
    title: str
    text: str
    links: list[str]
    crawled_at: datetime


class CrawlJob(BaseModel):
    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: CrawlStatus = CrawlStatus.PENDING
    url: str
    max_pages: int
    pages_crawled: int = 0
    pages: list[PageResult] = []
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class CrawlResponse(BaseModel):
    job_id: str
    status: CrawlStatus
    url: str
    pages_crawled: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class CrawlResultResponse(BaseModel):
    job_id: str
    status: CrawlStatus
    url: str
    pages_crawled: int
    pages: list[PageResult]
    started_at: datetime | None = None
    finished_at: datetime | None = None
