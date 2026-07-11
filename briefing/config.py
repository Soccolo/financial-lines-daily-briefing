from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    openai_api_key: str
    openai_model: str
    gmail_username: str
    gmail_app_password: str
    email_to: str
    article_count: int = 8
    timezone: str = "Europe/London"

    @classmethod
    def from_env(cls) -> "Config":
        required = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "").strip(),
            "GMAIL_USERNAME": os.getenv("GMAIL_USERNAME", "").strip(),
            "GMAIL_APP_PASSWORD": os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", ""),
            "EMAIL_TO": os.getenv("EMAIL_TO", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        article_count = int(os.getenv("ARTICLE_COUNT", "8"))
        if article_count not in (7, 8):
            raise ValueError("ARTICLE_COUNT must be 7 or 8")

        return cls(
            openai_api_key=required["OPENAI_API_KEY"],
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip(),
            gmail_username=required["GMAIL_USERNAME"],
            gmail_app_password=required["GMAIL_APP_PASSWORD"],
            email_to=required["EMAIL_TO"],
            article_count=article_count,
            timezone=os.getenv("TIMEZONE", "Europe/London").strip(),
        )

