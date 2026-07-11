from __future__ import annotations

import html
import smtplib
from datetime import datetime
from email.message import EmailMessage

from briefing.generate import Briefing
from briefing.news import Article


def _source_map(articles: list[Article]) -> dict[str, Article]:
    return {article.id: article for article in articles}


def render_text(briefing: Briefing, articles: list[Article], now: datetime, research_hours: int) -> str:
    sources = _source_map(articles)
    lines = [
        f"FINANCIAL LINES DAILY BRIEFING â€” {now:%d %b %Y}",
        f"Research window: previous {research_hours} hours | London date: {now:%d %B %Y}",
        "",
        "EXECUTIVE SUMMARY",
        *[f"â€¢ {item}" for item in briefing.executive_summary],
        "",
    ]
    for index, item in enumerate(briefing.articles, 1):
        source = sources[item.source_id]
        lines.extend(
            [
                f"{index}. {item.headline} [{item.category}]",
                item.summary,
                f"Pricing lens: {item.pricing_lens}",
                f"Source: {source.publisher} ({source.published_at:%d %b %Y, %H:%M UTC}) â€” {source.url}",
                "",
            ]
        )
    tutorial = briefing.tutorial
    lines.extend(
        [
            f"TODAY'S TUTORIAL â€” {tutorial.title}",
            f"{tutorial.category} | {tutorial.level}",
            tutorial.explanation,
            f"Formula: {tutorial.formula}" if tutorial.formula else "",
            f"Worked example: {tutorial.worked_example}",
            f"Practical use: {tutorial.practical_use}",
            f"Takeaway: {tutorial.takeaway}",
            "",
            "WHAT TO WATCH",
            *[f"â€¢ {item}" for item in briefing.what_to_watch],
            "",
            "Generated automatically from public sources. Verify material developments before business use.",
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def render_html(briefing: Briefing, articles: list[Article], now: datetime, research_hours: int) -> str:
    sources = _source_map(articles)
    executive = "".join(f"<li>{html.escape(item)}</li>" for item in briefing.executive_summary)
    story_blocks = []
    for index, item in enumerate(briefing.articles, 1):
        source = sources[item.source_id]
        story_blocks.append(
            f"""<section style="margin:0 0 24px">
            <h2 style="font-size:18px;margin:0 0 6px">{index}. {html.escape(item.headline)}</h2>
            <div style="color:#5b6573;font-size:13px;margin-bottom:8px">{html.escape(item.category)}</div>
            <p style="margin:0 0 8px">{html.escape(item.summary)}</p>
            <p style="margin:0 0 8px"><strong>Pricing lens:</strong> {html.escape(item.pricing_lens)}</p>
            <p style="margin:0"><a href="{html.escape(source.url, quote=True)}">{html.escape(source.publisher)}</a>
            Â· {source.published_at:%d %b %Y, %H:%M UTC}</p>
            </section>"""
        )
    tutorial = briefing.tutorial
    formula = f"<p><strong>Formula:</strong> <code>{html.escape(tutorial.formula)}</code></p>" if tutorial.formula else ""
    watch = "".join(f"<li>{html.escape(item)}</li>" for item in briefing.what_to_watch)
    return f"""<!doctype html><html><body style="margin:0;background:#f4f6f8;font-family:Arial,sans-serif;color:#17202a">
    <main style="max-width:760px;margin:auto;background:white;padding:32px">
    <h1 style="font-size:25px;margin:0 0 6px">Financial Lines Daily Briefing</h1>
    <p style="color:#5b6573;margin:0 0 24px">{now:%d %B %Y} Â· Previous {research_hours} hours</p>
    <h2 style="font-size:18px">Executive summary</h2><ul>{executive}</ul>
    <hr style="border:0;border-top:1px solid #dde2e7;margin:28px 0">
    {''.join(story_blocks)}
    <section style="background:#eef5ff;border-left:4px solid #2563eb;padding:20px;margin:30px 0">
      <div style="font-size:12px;color:#345;text-transform:uppercase">Today's tutorial Â· {html.escape(tutorial.category)} Â· {html.escape(tutorial.level)}</div>
      <h2 style="font-size:20px">{html.escape(tutorial.title)}</h2>
      <p>{html.escape(tutorial.explanation)}</p>{formula}
      <p><strong>Worked example:</strong> {html.escape(tutorial.worked_example)}</p>
      <p><strong>Practical use:</strong> {html.escape(tutorial.practical_use)}</p>
      <p><strong>Takeaway:</strong> {html.escape(tutorial.takeaway)}</p>
    </section>
    <h2 style="font-size:18px">What to watch</h2><ul>{watch}</ul>
    <p style="font-size:12px;color:#667085;margin-top:32px">Generated automatically from public sources. Verify material developments before business use.</p>
    </main></body></html>"""


def send_email(
    *,
    username: str,
    app_password: str,
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    message = EmailMessage()
    message["From"] = username
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(username, app_password)
        smtp.send_message(message)

