from datetime import datetime, timezone

from briefing.news import Article, canonical_url, deduplicate, normalise_title, select_candidates


def article(identifier: str, category: str, title: str, score: int, url: str) -> Article:
    return Article(
        id=identifier,
        category=category,
        title=title,
        publisher="Test source",
        url=url,
        published_at=datetime(2026, 7, 11, tzinfo=timezone.utc),
        snippet="Insurance pricing development",
        score=score,
    )


def test_normalise_title_removes_publisher_suffix():
    assert normalise_title("Cyber rates soften - Reuters") == "cyber rates soften"


def test_canonical_url_removes_query_and_fragment():
    assert canonical_url("HTTPS://Example.com/story/?utm_source=x#top") == "https://example.com/story"


def test_deduplicate_keeps_higher_scored_similar_story():
    items = [
        article("A1", "Cyber", "Cyber insurance rates soften - Reuters", 10, "https://a.test/1"),
        article("A2", "Cyber", "Cyber insurance rates soften", 6, "https://b.test/2"),
    ]
    result = deduplicate(items)
    assert [item.id for item in result] == ["A1"]


def test_select_candidates_limits_and_reassigns_ids():
    items = [
        article(str(index), "Cyber", f"Story {index}", 20 - index, f"https://x.test/{index}")
        for index in range(20)
    ]
    result = select_candidates(items, limit=14)
    assert len(result) == 14
    assert result[0].id == "A1"
    assert result[-1].id == "A14"
