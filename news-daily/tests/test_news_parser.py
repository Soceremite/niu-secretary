from pathlib import Path

from news_parser import parse_section_html


FIXTURES = Path(__file__).parent / "fixtures" / "sections"


def test_parse_valid_section_extracts_source_url():
    html = (FIXTURES / "sample_valid.html").read_text(encoding="utf-8")
    items = parse_section_html(html, section="ai")

    assert len(items) == 1
    item = items[0]
    assert item["id"] == "detail-ai-1"
    assert item["openId"] == "ai-1"
    assert item["section"] == "ai"
    assert item["title"] == "示例 AI 新闻标题"
    assert item["summary"] == "示例摘要。"
    assert item["sourceName"] == "示例媒体"
    assert item["sourceUrl"] == "https://example.com/news/article-1"
    assert "详情正文" in item["detailHtml"]


def test_parse_missing_source_sets_empty_source_url():
    html = (FIXTURES / "sample_invalid_missing_source.html").read_text(encoding="utf-8")
    items = parse_section_html(html, section="ai")

    assert len(items) == 1
    assert items[0]["sourceUrl"] == ""


def test_parse_suffix_detail_template_and_injects_missing_h2():
    html = """
    <a class="card-link" onclick="openDetail('ai-2'); return false;" href="#">
      <div class="news-card">
        <span class="tag tag-purple">AI</span>
        <h3>扩散文本模型发布</h3>
        <p class="card-summary">模型生成速度提升。</p>
      </div>
    </a>
    <template id="ai-2-detail">
      <div class="detail-meta">
        <span>📅 2026-06-17</span>
        <span>📰 示例媒体</span>
      </div>
      <div class="detail-keypoints">
        <div class="keypoint-card"><strong>并行生成</strong><p>生成速度提升。</p></div>
        <div class="keypoint-card"><strong>开源发布</strong><p>开发者可复用。</p></div>
      </div>
      <p>详情正文。</p>
      <a class="external-btn" href="https://example.com/news/article-2">阅读原文</a>
    </template>
    """

    items = parse_section_html(html, section="ai")

    assert len(items) == 1
    item = items[0]
    assert item["id"] == "detail-ai-2"
    assert item["openId"] == "ai-2"
    assert item["sourceName"] == "示例媒体"
    assert item["sourceUrl"] == "https://example.com/news/article-2"
    assert "<h2>扩散文本模型发布</h2>" in item["detailHtml"]
