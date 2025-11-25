import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from loguru import logger


class DataConnectorError(Exception):
    """Erro em conectores de dados."""


def normalize_item(content: str, title: str, url: str, source: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normaliza item para o formato interno."""
    item = {
        "content": content,
        "metadata": {
            "title": title,
            "url": url,
            "source": source,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }
    if extra:
        item["metadata"].update(extra)
    return item


async def fetch_rss(url: str, timeout: float = 10.0) -> List[Dict[str, Any]]:
    """Busca RSS e normaliza itens."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            raise DataConnectorError(f"RSS erro {resp.status_code}")
        import feedparser  # type: ignore
        feed = feedparser.parse(resp.text)
        items = []
        for e in feed.get("entries", [])[:20]:
            items.append(normalize_item(e.get("summary", ""), e.get("title", ""), e.get("link", url), "rss"))
        return items
    except Exception as e:
        logger.error(f"RSS falhou: {e}")
        return []


async def fetch_github_issues(repo: str, timeout: float = 10.0) -> List[Dict[str, Any]]:
    """Busca issues públicas do GitHub."""
    url = f"https://api.github.com/repos/{repo}/issues"
    try:
        async with httpx.AsyncClient(timeout=timeout, headers={"Accept": "application/vnd.github+json"}) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            raise DataConnectorError(f"GitHub erro {resp.status_code}")
        data = resp.json()
        items = []
        for issue in data[:20]:
            if issue.get("pull_request"):
                continue
            items.append(normalize_item(issue.get("body", ""), issue.get("title", ""), issue.get("html_url", url), "github", {"number": issue.get("number")}))
        return items
    except Exception as e:
        logger.error(f"GitHub falhou: {e}")
        return []


async def fetch_wikipedia(query: str, timeout: float = 10.0) -> List[Dict[str, Any]]:
    """Busca resumo no Wikipedia REST."""
    try:
        title = query.replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
        if resp.status_code == 404:
            return []
        if resp.status_code >= 400:
            raise DataConnectorError(f"Wikipedia erro {resp.status_code}")
        data = resp.json()
        content = data.get("extract", "")
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page", url)
        return [normalize_item(content, data.get("title", query), page_url, "wikipedia")]
    except Exception as e:
        logger.error(f"Wikipedia falhou: {e}")
        return []


async def fetch_all(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Busca dados de múltiplas fontes com fallback."""
    tasks = []
    for s in sources:
        t = s.get("type")
        if t == "rss":
            tasks.append(fetch_rss(s["url"]))
        elif t == "github_issues":
            tasks.append(fetch_github_issues(s["repo"]))
        elif t == "wikipedia":
            tasks.append(fetch_wikipedia(s["query"]))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: List[Dict[str, Any]] = []
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Fonte falhou: {r}")
            continue
        items.extend(r)
    return items

