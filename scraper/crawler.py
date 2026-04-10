from __future__ import annotations

import asyncio
import logging
from fnmatch import fnmatch
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import aiohttp

from .models import CrawlJob, CrawlStatus, PageResult
from .parser import extract_links, extract_text, extract_title

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "FastWebScraper/1.0 (+https://github.com/example/fast-website-scraper)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.5",
}


async def _fetch_robots(session: aiohttp.ClientSession, base_url: str) -> RobotFileParser | None:
    rp = RobotFileParser()
    robots_url = f"{base_url}/robots.txt"
    try:
        async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                text = await resp.text()
                rp.parse(text.splitlines())
                return rp
    except Exception:
        logger.debug("Could not fetch robots.txt for %s", base_url)
    return None


def _same_domain(url: str, base_domain: str) -> bool:
    return urlparse(url).netloc == base_domain


def _path_matches(path: str, pattern: str) -> bool:
    """Match a URL path against a glob pattern, normalizing slashes."""
    path = path.strip("/")
    pattern = pattern.strip("/")
    return fnmatch(path, pattern)


def _url_matches_filters(
    url: str,
    exclude_paths: list[str],
    include_paths: list[str],
) -> bool:
    """Return True if the URL should be crawled based on path filters."""
    path = urlparse(url).path
    if include_paths and not any(_path_matches(path, p) for p in include_paths):
        return False
    if any(_path_matches(path, p) for p in exclude_paths):
        return False
    return True


async def crawl(
    job: CrawlJob,
    max_concurrency: int = 10,
    delay: float = 0.2,
    respect_robots: bool = True,
    exclude_paths: list[str] | None = None,
    include_paths: list[str] | None = None,
) -> None:
    _exclude = exclude_paths or []
    _include = include_paths or []

    job.status = CrawlStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)

    parsed_start = urlparse(job.url)
    base_domain = parsed_start.netloc
    base_url = f"{parsed_start.scheme}://{parsed_start.netloc}"

    visited: set[str] = set()
    queue: asyncio.Queue[str] = asyncio.Queue()
    queue.put_nowait(job.url)

    semaphore = asyncio.Semaphore(max_concurrency)

    connector = aiohttp.TCPConnector(limit=max_concurrency, ssl=False)
    timeout = aiohttp.ClientTimeout(total=30)

    try:
        async with aiohttp.ClientSession(headers=_HEADERS, connector=connector, timeout=timeout) as session:
            robots: RobotFileParser | None = None
            if respect_robots:
                robots = await _fetch_robots(session, base_url)

            async def process_url(url: str) -> None:
                if url in visited or len(visited) >= job.max_pages:
                    return
                visited.add(url)

                if not _url_matches_filters(url, _exclude, _include):
                    logger.debug("Filtered out: %s", url)
                    return

                if robots and not robots.can_fetch(_HEADERS["User-Agent"], url):
                    logger.debug("Blocked by robots.txt: %s", url)
                    return

                async with semaphore:
                    if delay > 0:
                        await asyncio.sleep(delay)
                    try:
                        async with session.get(url) as resp:
                            if resp.status != 200:
                                return
                            content_type = resp.headers.get("Content-Type", "")
                            if "text/html" not in content_type:
                                return
                            html = await resp.text(errors="replace")
                    except Exception as e:
                        logger.warning("Failed to fetch %s: %s", url, e)
                        return

                text = extract_text(html)
                title = extract_title(html)
                links = extract_links(html, url)

                page = PageResult(
                    url=url,
                    title=title,
                    text=text,
                    links=links,
                    crawled_at=datetime.now(timezone.utc),
                )
                job.pages.append(page)
                job.pages_crawled = len(job.pages)

                for link in links:
                    if _same_domain(link, base_domain) and link not in visited and len(visited) < job.max_pages:
                        queue.put_nowait(link)

            while not queue.empty() and len(visited) < job.max_pages:
                batch: list[str] = []
                while not queue.empty() and len(batch) < max_concurrency:
                    batch.append(queue.get_nowait())

                await asyncio.gather(*(process_url(url) for url in batch))

        job.status = CrawlStatus.COMPLETED
    except Exception as e:
        job.status = CrawlStatus.FAILED
        job.error = str(e)
        logger.error("Crawl failed for %s: %s", job.url, e)
    finally:
        job.finished_at = datetime.now(timezone.utc)
