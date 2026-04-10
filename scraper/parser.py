from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

_STRIP_TAGS = {"script", "style", "noscript", "svg", "head"}


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()
    lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
    return "\n".join(line for line in lines if line)


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme in ("http", "https"):
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean += f"?{parsed.query}"
            links.append(clean)
    return links
