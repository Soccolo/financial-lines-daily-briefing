from __future__ import annotations

import email
import html
import imaplib
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.header import decode_header
from time import mktime
from urllib.parse import quote_plus, urlsplit, urlunsplit

import feedparser
import requests
import trafilatura
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

SEARCHES = {
    "Actuarial & Pricing": '(actuarial OR "insurance pricing" OR reserving OR reinsurance) insurance',
    "Cyber": '("cyber insurance" OR ransomware OR "data breach") insurance',
    "D&O / PI": '("directors and officers" OR "D&O insurance" OR "professional indemnity")',
    "M&A": '("mergers and acquisitions" OR "M&A") insurance risk',
    "Financial Institutions": '("financial institutions insurance" OR fintech OR banking liability) regulation',
    "Accident & Health": '("accident and health insurance" OR "A&H insurance" OR health insurance)',
    "Industry & Legislation": '(FCA OR PRA OR EIOPA OR Lloyds OR "London market") insurance regulation',
}

KEYWORDS = {
    "insurance": 3,
    "pricing": 4,
    "actuar": 4,
    "cyber": 5,
    "ransomware": 4,
    "merger": 3,
    "acquisition": 3,
    "director": 4,
    "professional indemnity": 5,
    "financial institution": 4,
    "accident and health": 4,
    "fca": 4,
    "pra": 4,
    "eiopa": 4,
    "lloyd": 4,
    "regulation": 3,
    "legislation": 3,
    "claims": 3,
    "capacity": 2,
}

TRUSTED_SOURCES = (
    "fca",
    "bank of england",
    "gov.uk",
    "eiopa",
    "lloyd",
    "reuters",
    "financial times",
    "insurance journal",
    "the insurer",
    "artemis",
)


@dataclass(frozen=True)
class Article:
    id: str
    category: str
    title: str
    publisher: str
    url: str
    published_at: datetime
    snippet: str
    text: str = ""
    score: int = 0


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(html.unescape(value or ""), "html.parser").get_text(" ")).strip()


def normalise_title(title: str) -> str:
    title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title.lower())
    return re.sub(r"[^a-z0-9]+", " ", title).strip()


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def _published(entry: object) -> datetime:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _score(article: Article) -> int:
    haystack = f"{article.title} {article.snippet} {article.publisher}".lower()
    score = sum(weight for term, weight in KEYWORDS.items() if term in haystack)
    score += 4 if any(source in article.publisher.lower() for source in TRUSTED_SOURCES) else 0
    age_hours = max(0, (datetime.now(timezone.utc) - article.published_at).total_seconds() / 3600)
    score += max(0, 5 - int(age_hours // 12))
    return score


def collect_articles(hours: int = 36, per_category: int = 8) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    articles: list[Article] = []
    counter = 0
    for category, query in SEARCHES.items():
        rss_url = (
            "https://news.google.com/rss/search?q="
            f"{quote_plus(query + ' when:2d')}&hl=en-GB&gl=GB&ceid=GB:en"
        )
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:per_category]:
            published_at = _published(entry)
            if published_at < cutoff:
                continue
            counter += 1
            source = getattr(getattr(entry, "source", None), "title", "") or "Unknown source"
            article = Article(
                id=f"A{counter}",
                category=category,
                title=_clean_text(getattr(entry, "title", "")),
                publisher=_clean_text(source),
                url=getattr(entry, "link", ""),
                published_at=published_at,
                snippet=_clean_text(getattr(entry, "summary", ""))[:700],
            )
            articles.append(replace(article, score=_score(article)))
    return deduplicate(articles)


def deduplicate(articles: list[Article]) -> list[Article]:
    kept: list[Article] = []
    for candidate in sorted(articles, key=lambda item: (item.score, item.published_at), reverse=True):
        candidate_title = normalise_title(candidate.title)
        if not candidate_title or not candidate.url:
            continue
        if any(
            SequenceMatcher(None, candidate_title, normalise_title(existing.title)).ratio() >= 0.86
            for existing in kept
        ):
            continue
        kept.append(candidate)
    return kept


def select_candidates(articles: list[Article], limit: int = 14) -> list[Article]:
    selected: list[Article] = []
    for category in SEARCHES:
        category_items = [item for item in articles if item.category == category]
        selected.extend(category_items[:2])
    seen = {item.url for item in selected}
    for article in articles:
        if len(selected) >= limit:
            break
        if article.url not in seen:
            selected.append(article)
            seen.add(article.url)
    selected = selected[:limit]
    return [replace(article, id=f"A{index}") for index, article in enumerate(selected, 1)]


def _fetch_article(article: Article, max_chars: int = 2200) -> Article:
    try:
        response = requests.get(
            article.url,
            timeout=15,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FinancialLinesBriefing/1.0)"},
        )
        response.raise_for_status()
        resolved_url = canonical_url(response.url)
        extracted = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        text = _clean_text(extracted or article.snippet)[:max_chars]
        return replace(article, url=resolved_url, text=text)
    except Exception as exc:  # A failed publisher page should not abort the whole briefing.
        LOGGER.warning("Could not fetch %s: %s", article.url, exc)
        return replace(article, text=article.snippet[:max_chars])


def enrich_articles(articles: list[Article]) -> list[Article]:
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(_fetch_article, articles))


def _decode_subject(raw_subject: str | None) -> str:
    parts = []
    for value, encoding in decode_header(raw_subject or ""):
        parts.append(value.decode(encoding or "utf-8", errors="replace") if isinstance(value, bytes) else value)
    return "".join(parts)


def sent_briefing_today(username: str, app_password: str, subject: str) -> bool:
    """Return whether the exact daily briefing subject already appears in Sent Mail."""
    try:
        with imaplib.IMAP4_SSL("imap.gmail.com") as mailbox:
            mailbox.login(username, app_password)
            status, _ = mailbox.select('"[Gmail]/Sent Mail"', readonly=True)
            if status != "OK":
                return False
            since = datetime.now().strftime("%d-%b-%Y")
            status, data = mailbox.search(None, "SINCE", since, "SUBJECT", '"Financial Lines Daily Briefing"')
            if status != "OK" or not data:
                return False
            for message_id in data[0].split()[-10:]:
                status, payload = mailbox.fetch(message_id, "(RFC822.HEADER)")
                if status != "OK" or not payload or not isinstance(payload[0], tuple):
                    continue
                message = email.message_from_bytes(payload[0][1])
                if _decode_subject(message.get("Subject")) == subject:
                    return True
    except Exception as exc:
        LOGGER.warning("Could not check whether today's briefing was sent: %s", exc)
    return False


def recent_sent_urls(username: str, app_password: str, days: int = 7) -> set[str]:
    urls: set[str] = set()
    try:
        with imaplib.IMAP4_SSL("imap.gmail.com") as mailbox:
            mailbox.login(username, app_password)
            status, _ = mailbox.select('"[Gmail]/Sent Mail"', readonly=True)
            if status != "OK":
                return urls
            since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            status, data = mailbox.search(None, "SINCE", since, "SUBJECT", '"Financial Lines Daily Briefing"')
            if status != "OK" or not data:
                return urls
            for message_id in data[0].split()[-10:]:
                status, payload = mailbox.fetch(message_id, "(RFC822)")
                if status != "OK" or not payload or not isinstance(payload[0], tuple):
                    continue
                message = email.message_from_bytes(payload[0][1])
                if "Financial Lines Daily Briefing" not in _decode_subject(message.get("Subject")):
                    continue
                for part in message.walk() if message.is_multipart() else [message]:
                    if part.get_content_type() not in ("text/plain", "text/html"):
                        continue
                    body = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    text = body.decode(charset, errors="replace")
                    urls.update(canonical_url(url) for url in re.findall(r"https?://[^\s<>\"]+", text))
    except Exception as exc:
        LOGGER.warning("Could not read recent sent mail for deduplication: %s", exc)
    return urls


def exclude_recent(articles: list[Article], recent_urls: set[str]) -> list[Article]:
    return [article for article in articles if canonical_url(article.url) not in recent_urls]

