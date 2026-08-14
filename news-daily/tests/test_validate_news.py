from news_daily_validate import is_rejected_source_url, validate_items
from validate_news import validate_payload


def test_rejects_search_urls():
    assert is_rejected_source_url("https://www.baidu.com/s?wd=test")
    assert is_rejected_source_url("https://cn.bing.com/search?q=test")
    assert is_rejected_source_url("#")
    assert is_rejected_source_url("javascript:void(0)")


def test_allows_article_url():
    assert not is_rejected_source_url("https://news.example.com/a/2026/0614/story.html")


def test_validate_items_requires_source_url():
    errors = validate_items(
        [
            {
                "id": "detail-ai-1",
                "section": "ai",
                "title": "标题",
                "summary": "摘要",
                "sourceUrl": "",
                "detailHtml": '<h2>标题</h2><div class="detail-meta">📅 2026-06-14</div><p>正文</p>',
            }
        ]
    )
    assert any("missing sourceUrl" in error for error in errors)


def test_validate_items_requires_structured_keypoints():
    errors = validate_items(
        [
            {
                "id": "detail-ai-1",
                "section": "ai",
                "title": "标题",
                "summary": "摘要",
                "sourceUrl": "https://example.com/news/article-1",
                "detailHtml": (
                    '<h2>标题</h2><div class="detail-meta">📅 2026-06-14</div>'
                    "<p>正文</p>"
                    '<a class="external-btn" href="https://example.com/news/article-1">阅读原文</a>'
                ),
            }
        ]
    )
    assert any("missing detail-keypoints" in error for error in errors)


def test_validate_items_requires_multiple_keypoint_cards():
    errors = validate_items(
        [
            {
                "id": "detail-ai-1",
                "section": "ai",
                "title": "标题",
                "summary": "摘要",
                "sourceUrl": "https://example.com/news/article-1",
                "detailHtml": (
                    '<h2>标题</h2><div class="detail-meta">📅 2026-06-14</div>'
                    '<div class="detail-keypoints">'
                    '<div class="keypoint-card"><span>事件</span><strong>正文</strong></div>'
                    "</div>"
                    "<p>正文</p>"
                    '<a class="external-btn" href="https://example.com/news/article-1">阅读原文</a>'
                ),
            }
        ]
    )
    assert any("expected at least 2 keypoint-card" in error for error in errors)


def test_validate_payload_strict_sources_rejects_reused_url():
    payload = {
        "items": [
            {
                "id": "detail-ai-1",
                "section": "ai",
                "title": "标题一",
                "summary": "摘要",
                "sourceUrl": "https://example.com/news/article-1.html",
                "detailHtml": (
                    '<h2>标题一</h2><div class="detail-meta">📅 2026-06-14</div>'
                    '<div class="detail-keypoints">'
                    '<div class="keypoint-card"><span>事件</span><strong>正文</strong></div>'
                    '<div class="keypoint-card"><span>影响</span><strong>正文</strong></div>'
                    "</div>"
                    "<p>正文</p>"
                    '<a class="external-btn" href="https://example.com/news/article-1.html">阅读原文</a>'
                ),
            },
            {
                "id": "detail-ai-2",
                "section": "ai",
                "title": "标题二",
                "summary": "摘要",
                "sourceUrl": "https://example.com/news/article-1.html",
                "detailHtml": (
                    '<h2>标题二</h2><div class="detail-meta">📅 2026-06-14</div>'
                    '<div class="detail-keypoints">'
                    '<div class="keypoint-card"><span>事件</span><strong>正文</strong></div>'
                    '<div class="keypoint-card"><span>影响</span><strong>正文</strong></div>'
                    "</div>"
                    "<p>正文</p>"
                    '<a class="external-btn" href="https://example.com/news/article-1.html">阅读原文</a>'
                ),
            },
        ]
    }

    errors = validate_payload(payload, strict_sources=True)

    assert any("sourceUrl reused by 2 items" in error for error in errors)
