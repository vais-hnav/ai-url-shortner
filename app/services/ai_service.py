import json
import logging
import re
from collections import Counter
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_insight import AIInsight
from app.models.url import ShortenedURL

MAX_FETCH_BYTES = 200_000
FETCH_TIMEOUT_SECONDS = 10.0
LLM_INPUT_CHAR_LIMIT = 8000
STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "your",
    "have",
    "are",
    "you",
    "into",
    "how",
    "what",
    "when",
    "where",
    "will",
    "also",
}
logger = logging.getLogger(__name__)


def _validate_fetch_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported.")
    if not parsed.netloc:
        raise ValueError("Invalid URL.")
    blocked_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.hostname in blocked_hosts:
        raise ValueError("Localhost URLs are not allowed for AI fetch.")


def _is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.endswith("youtube.com") or host.endswith("youtu.be")


async def _fetch_youtube_oembed_text(url: str) -> str | None:
    endpoint = "https://www.youtube.com/oembed"
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS) as client:
        response = await client.get(endpoint, params={"url": url, "format": "json"})
    if response.status_code >= 400:
        return None
    payload = response.json()
    title = str(payload.get("title", "")).strip()
    author = str(payload.get("author_name", "")).strip()
    provider = str(payload.get("provider_name", "YouTube")).strip()
    if not title:
        return None
    parts = [
        f"Title: {title}.",
        f"Creator: {author}." if author else "",
        f"Platform: {provider}.",
        "This is a video page; summarize using title and creator context.",
    ]
    return " ".join(part for part in parts if part).strip()


def _clean_html_to_text(html: str) -> str:
    # Remove non-content blocks first.
    cleaned = re.sub(
        r"<(script|style|noscript|svg|canvas|iframe)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r"<(nav|header|footer|aside|form)[^>]*>.*?</\1>",
        " ",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Prefer semantic content regions when available.
    preferred_blocks = re.findall(
        r"<(main|article)[^>]*>(.*?)</\1>",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    preferred_html = " ".join(block for _tag, block in preferred_blocks) if preferred_blocks else cleaned

    # Pull useful metadata signals.
    title_match = re.search(r"<title[^>]*>(.*?)</title>", cleaned, flags=re.IGNORECASE | re.DOTALL)
    meta_desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    og_desc_match = re.search(
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    title_text = title_match.group(1).strip() if title_match else ""
    description_text = (
        (meta_desc_match.group(1).strip() if meta_desc_match else "")
        or (og_desc_match.group(1).strip() if og_desc_match else "")
    )

    # Strip remaining tags and normalize whitespace.
    no_tags = re.sub(r"<[^>]+>", " ", preferred_html)
    no_urls = re.sub(r"https?://\S+", " ", no_tags)
    compact = re.sub(r"\s+", " ", no_urls).strip()

    # Remove common web chrome fragments.
    chrome_noise = [
        "cookie",
        "privacy policy",
        "terms of service",
        "sign in",
        "log in",
        "subscribe",
        "menu",
        "search",
    ]
    for token in chrome_noise:
        compact = re.sub(rf"\b{re.escape(token)}\b", " ", compact, flags=re.IGNORECASE)
    compact = re.sub(r"\s+", " ", compact).strip()

    combined = " ".join(part for part in [title_text, description_text, compact] if part).strip()
    return combined


def _summarize_text(text: str) -> str:
    if not text:
        return "No meaningful page text could be extracted."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    useful_sentences: list[str] = []
    for sentence in sentences:
        cleaned = sentence.strip()
        if len(cleaned) < 40:
            continue
        if re.search(r"[{};$<>]", cleaned):
            continue
        useful_sentences.append(cleaned)
        if len(useful_sentences) == 2:
            break
    summary = " ".join(useful_sentences).strip()
    return summary[:320] if summary else text[:320]


def _extract_tags(text: str, top_n: int = 5) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    common = Counter(filtered).most_common(top_n)
    return [w for w, _ in common] or ["general"]


def _coerce_llm_result(content: str) -> tuple[str, list[str]]:
    text = content.strip()
    json_candidate_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    json_candidate = json_candidate_match.group(0) if json_candidate_match else text
    payload = json.loads(json_candidate)

    summary = str(payload.get("summary", "")).strip()
    tags_raw = payload.get("tags", [])
    if isinstance(tags_raw, list):
        tags = [str(tag).strip().lower() for tag in tags_raw if str(tag).strip()]
    else:
        tags = []

    if not summary:
        raise ValueError("LLM response did not include summary.")
    if not tags:
        tags = ["general"]
    return summary[:320], tags[:5]


def _normalize_gemini_model_name(model: str) -> str:
    normalized = model.strip()
    if normalized.startswith("models/"):
        normalized = normalized.split("/", 1)[1]
    return normalized


def _pick_preferred_model(model_names: list[str]) -> str | None:
    if not model_names:
        return None
    priority_tokens = [
        "2.5-flash",
        "2.0-flash",
        "1.5-flash",
        "flash",
        "pro",
    ]
    for token in priority_tokens:
        for name in model_names:
            if token in name:
                return name
    return model_names[0]


async def _resolve_generate_content_model() -> str:
    configured = _normalize_gemini_model_name(settings.gemini_primary_model)

    async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
        response = await client.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": settings.gemini_api_key},
        )
    if response.status_code >= 400:
        raise ValueError(f"Gemini model list HTTP {response.status_code}: {response.text[:300]}")

    payload = response.json()
    models = payload.get("models", [])
    compatible: list[str] = []
    for model in models:
        supported_methods = model.get("supportedGenerationMethods", [])
        name = model.get("name", "")
        if "generateContent" in supported_methods and name.startswith("models/"):
            compatible.append(name.split("/", 1)[1])

    if configured in compatible:
        return configured

    chosen = _pick_preferred_model(compatible)
    if not chosen:
        raise ValueError("No Gemini model with generateContent support is available for this API key.")

    logger.warning(
        "Configured Gemini model '%s' is unavailable for generateContent; using '%s' instead.",
        configured,
        chosen,
    )
    return chosen


async def _summarize_with_gemini_model(
    model: str, original_url: str, page_text: str
) -> tuple[str, list[str], str]:
    model_name = _normalize_gemini_model_name(model)
    prompt = (
        "You are an assistant for a URL intelligence platform. "
        "Given a URL and page text, return strict JSON with keys: "
        '"summary" (max 2 sentences) and "tags" (3-5 short lowercase tags). '
        "No markdown, no extra keys."
    )

    trimmed_text = page_text[:LLM_INPUT_CHAR_LIMIT]
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"{prompt}\n\n"
                            f"URL: {original_url}\n\n"
                            f"PAGE_TEXT:\n{trimmed_text}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
            params={"key": settings.gemini_api_key},
            json=body,
        )
    if response.status_code >= 400:
        raise ValueError(f"Gemini HTTP {response.status_code}: {response.text[:300]}")
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"Gemini returned no candidates: {str(data)[:300]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError(f"Gemini returned no content parts: {str(data)[:300]}")
    content = parts[0].get("text", "")
    if not content:
        raise ValueError(f"Gemini returned empty text: {str(data)[:300]}")
    summary, tags = _coerce_llm_result(content)
    return summary, tags, model_name


async def fetch_page_text(url: str) -> str:
    _validate_fetch_url(url)
    if _is_youtube_url(url):
        yt_text = await _fetch_youtube_oembed_text(url)
        if yt_text:
            return yt_text

    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
        response = await client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        raise ValueError("Only HTML pages are supported for summarization.")
    content = response.text[:MAX_FETCH_BYTES]
    return _clean_html_to_text(content)


async def summarize_url(original_url: str) -> tuple[str, list[str], str, str | None]:
    text = await fetch_page_text(original_url)
    if settings.ai_provider.lower() == "gemini" and settings.gemini_api_key:
        try:
            model_name = await _resolve_generate_content_model()
            summary, tags, used_model = await _summarize_with_gemini_model(
                model_name, original_url, text
            )
            return summary, tags, f"gemini:{used_model}", None
        except Exception as exc:
            logger.exception("Gemini summarize failed.")
            fallback_reason = str(exc)[:300]
    else:
        fallback_reason = "Gemini provider disabled or API key missing."

    summary = _summarize_text(text)
    tags = _extract_tags(text)
    return summary, tags, "extractive-fallback", fallback_reason


async def create_ai_insight(
    db: AsyncSession,
    original_url: str,
    summary: str,
    tags: list[str],
    user_id: int | None = None,
    short_code: str | None = None,
) -> AIInsight:
    url_id: int | None = None
    if short_code:
        shortened_url = await db.scalar(
            select(ShortenedURL).where(ShortenedURL.short_code == short_code)
        )
        if shortened_url:
            url_id = shortened_url.id

    insight = AIInsight(
        user_id=user_id,
        url_id=url_id,
        original_url=original_url,
        summary=summary,
        tags=",".join(tags),
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)
    return insight
