import subprocess

from audit_news_sources import (
    _fetch_page_title_with_curl,
    collect_source_issues,
    cross_section_duplicate_pairs,
    event_group_key,
    is_generic_source_url,
    is_high_risk_item,
    source_title_matches,
)


def test_detects_generic_source_urls():
    assert is_generic_source_url("https://example.com/news/list")
    assert is_generic_source_url("https://example.com/stock/index.shtml")
    assert not is_generic_source_url("https://example.com/news/20260618/article-1.html")


def test_detects_reused_source_urls():
    issues = collect_source_issues(
        [
            {"id": "detail-ai-1", "title": "A", "sourceUrl": "https://example.com/a.html"},
            {"id": "detail-ai-2", "title": "B", "sourceUrl": "https://example.com/a.html"},
        ]
    )
    assert any("reused by 2 items" in issue for issue in issues)


def test_detects_title_mismatch_when_source_title_available():
    issues = collect_source_issues(
        [{"id": "detail-ai-1", "title": "OpenAI 财报泄密", "sourceUrl": "https://example.com/a.html"}],
        source_titles={"https://example.com/a.html": "全国铁路7月1日起调图"},
    )
    assert any("does not match source page title" in issue for issue in issues)


def test_allows_related_title():
    assert source_title_matches("OpenAI财报泄密：2025年净亏损385亿美元", "炸裂！OpenAI财报泄密：去年亏了2600亿")


def test_curl_fallback_extracts_page_title():
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="<html><title>VOA source title</title></html>\n200",
        )

    original_run = subprocess.run
    subprocess.run = fake_run
    try:
        assert _fetch_page_title_with_curl("https://example.com/article", 12) == (
            200,
            "VOA source title",
        )
    finally:
        subprocess.run = original_run


def test_high_risk_items_require_live_title_verification():
    issues = collect_source_issues(
        [{"id": "detail-ai-1", "title": "OpenAI 推出 GPT-6", "sourceUrl": "https://example.com/a.html"}],
        source_titles={},
    )

    assert any("high-risk item requires live source title verification" in issue for issue in issues)
    assert is_high_risk_item({"title": "强震遇难人数升至3889人"})


def test_detects_cross_section_event_repetition():
    items = [
        {"id": "detail-domestic-1", "title": "火箭网系回收成功", "sourceUrl": "https://example.com/a.html"},
        {"id": "detail-finance-1", "title": "全球首次火箭网系回收成功 多家A股公司参与", "sourceUrl": "https://example.com/b.html"},
        {"id": "detail-tech-1", "title": "中国可复用火箭回收时代开启", "sourceUrl": "https://example.com/c.html"},
    ]

    issues = collect_source_issues(items, source_titles={item["sourceUrl"]: item["title"] for item in items})

    assert event_group_key(items[0]) == "rocket-recovery"
    assert any("event group rocket-recovery appears 3 times" in issue for issue in issues)


def test_detects_generic_cross_section_ai_tech_duplicate():
    items = [
        {
            "id": "detail-tech-1",
            "section": "tech",
            "title": "英伟达推出30B开源AI模型Nemotron 3.5 Lightning",
            "summary": "NVIDIA 发布 300 亿参数开源模型，主打高效推理。",
            "sourceUrl": "https://example.com/nvidia-nemotron-tech.html",
        },
        {
            "id": "detail-ai-1",
            "section": "ai",
            "title": "NVIDIA发布Nemotron 3.5 Lightning开源模型",
            "summary": "英伟达新模型面向 AI 推理场景，参数规模约 30B。",
            "sourceUrl": "https://example.org/nemotron-ai.html",
        },
    ]

    pairs = cross_section_duplicate_pairs(items)
    issues = collect_source_issues(items, source_titles={item["sourceUrl"]: item["title"] for item in items})

    assert pairs
    assert pairs[0][0]["id"] == "detail-tech-1"
    assert pairs[0][1]["id"] == "detail-ai-1"
    assert any("cross-section similar event" in issue for issue in issues)


def test_allows_distinct_ai_adjacent_cross_section_stories():
    items = [
        {
            "id": "detail-finance-1",
            "section": "finance",
            "title": "工业富联上半年净利润大增，AI服务器需求强劲",
            "summary": "AI服务器订单推动业绩增长。",
            "sourceUrl": "https://example.com/foxconn-ai-server.html",
        },
        {
            "id": "detail-ai-1",
            "section": "ai",
            "title": "OpenAI高管宣布离职创业，奥尔特曼发文感谢",
            "summary": "OpenAI 商业运营高管离职创业。",
            "sourceUrl": "https://example.org/openai-exec.html",
        },
    ]

    assert cross_section_duplicate_pairs(items) == []
