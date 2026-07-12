from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from briefing.config import Config
from briefing.emailer import render_html, render_text, send_email
from briefing.generate import generate_briefing
from briefing.news import (
    collect_articles,
    enrich_articles,
    exclude_recent,
    recent_sent_urls,
    sent_briefing_today,
    select_candidates,
)


def should_run(now: datetime) -> bool:
    """Allow late GitHub schedules through the morning, but not all day."""
    return os.getenv("GITHUB_EVENT_NAME") != "schedule" or 7 <= now.hour < 12


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = Config.from_env()
    now = datetime.now(ZoneInfo(config.timezone))
    if not should_run(now):
        logging.info("Skipping scheduled run outside the 07:00-12:00 London delivery window")
        return

    subject = f"Financial Lines Daily Briefing — {now:%d %b %Y}"
    if sent_briefing_today(config.gmail_username, config.gmail_app_password, subject):
        logging.info("Briefing already sent for the London date %s", now.date())
        return

    recent_urls = recent_sent_urls(config.gmail_username, config.gmail_app_password)
    research_hours = 36
    articles = exclude_recent(collect_articles(hours=research_hours), recent_urls)
    candidates = select_candidates(articles)
    if len(candidates) < config.article_count:
        logging.info("Only %s recent candidates; widening research window to 72 hours", len(candidates))
        research_hours = 72
        candidates = select_candidates(exclude_recent(collect_articles(hours=research_hours, per_category=12), recent_urls))
    candidates = enrich_articles(candidates)

    briefing = generate_briefing(
        candidates,
        api_key=config.openai_api_key,
        model=config.openai_model,
        article_count=config.article_count,
        now=now,
    )
    subject = f"Financial Lines Daily Briefing — {now:%d %b %Y}"
    html_body, inline_images = render_html(briefing, candidates, now, research_hours)
    send_email(
        username=config.gmail_username,
        app_password=config.gmail_app_password,
        recipient=config.email_to,
        subject=subject,
        text_body=render_text(briefing, candidates, now, research_hours),
        html_body=html_body,
        inline_images=inline_images,
    )
    logging.info("Sent %s articles using %s", len(briefing.articles), config.openai_model)


if __name__ == "__main__":
    run()

