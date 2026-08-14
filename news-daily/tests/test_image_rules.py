from pathlib import Path

from image_rules import extract_image_candidates, reject_reason


FIXTURES = Path(__file__).parent / "fixtures" / "images"


def test_reject_reason_catches_logo_and_qrcode():
    assert reject_reason("https://example.com/logo.png", "site logo") == "REJECTED_LOGO"
    assert reject_reason("https://example.com/qrcode.png", "二维码") == "REJECTED_QRCODE"


def test_extract_candidates_prefers_article_content_image():
    html = (FIXTURES / "article_with_logo_and_content.html").read_text(encoding="utf-8")
    candidates = extract_image_candidates(html, "https://example.com/news/story.html", "示例新闻标题")

    assert candidates[0]["url"] == "https://example.com/uploads/2026/06/content-main.jpg"
    assert candidates[0]["status"] == "OK"


def test_rejects_footer_and_site_default_images():
    html = """
    <main class="article-content">
      <h1>新闻标题</h1>
      <p>正文。</p>
    </main>
    <footer>
      <img src="/images/footer032.png" alt="footer" width="477" height="260">
    </footer>
    <img src="/common/newslog200.jpg" width="400" height="200">
    <img src="/assets/0516_zwKeyWordBanner.jpeg" width="900" height="220">
    """
    candidates = extract_image_candidates(html, "https://example.com/news/story.html", "新闻标题")
    statuses = {candidate["url"]: candidate["status"] for candidate in candidates}

    assert statuses["https://example.com/images/footer032.png"] in {
        "REJECTED_LOGO",
        "REJECTED_PLACEHOLDER",
    }
    assert statuses["https://example.com/common/newslog200.jpg"] == "REJECTED_LOGO"
    assert statuses["https://example.com/assets/0516_zwKeyWordBanner.jpeg"] == "REJECTED_LOGO"


def test_prefers_36kr_image_wrapper_lead_image():
    html = """
    <main class="article-content">
      <h1>突发！Anthropic全球停用Claude 5</h1>
      <p>究竟为何，Anthropic突然下线了地表最强Claude？</p>
      <p class="image-wrapper"><img data-img-size-val="1080,463"
        src="https://img.36krcdn.com/hsossms/20260613/v2_74565134293746cf8b34869e6309d618@5579416_oswg82577oswg1080oswg463_img_000?x-oss-process=image/format,jpg/interlace,1"></p>
      <p>正文。</p>
      <p class="image-wrapper"><img data-img-size-val="1080,1001"
        src="https://img.36krcdn.com/hsossms/20260613/v2_2a65dd0d40de451bbfbf541b7290acef@5579416_oswg142424oswg1080oswg1001_img_000?x-oss-process=image/format,jpg/interlace,1"></p>
    </main>
    """
    candidates = extract_image_candidates(
        html,
        "https://36kr.com/p/3851015329027336",
        "Anthropic全球停用Claude Fable 5和Mythos 5，发布仅72小时",
    )

    assert candidates[0]["url"].startswith(
        "https://img.36krcdn.com/hsossms/20260613/v2_74565134293746cf8b34869e6309d618"
    )
    assert candidates[0]["status"] == "OK"


def test_prefers_lazy_loaded_original_over_placeholder_src():
    html = """
    <div class="post_content" id="paragraph">
      <h1>比亚迪王朝首款 D 级旗舰轿车，大汉实车曝光</h1>
      <p style="text-align: center;">
        <img
          src="//img.ithome.com/images/v2/t.png"
          class="lazy"
          title="比亚迪王朝首款 D 级旗舰轿车，大汉实车曝光"
          data-original="https://img.ithome.com/newsuploadfiles/2026/7/car.jpg?x-bce-process=image/format,f_auto"
          width="1423"
          height="2481"
        >
      </p>
    </div>
    """

    candidates = extract_image_candidates(
        html,
        "https://www.ithome.com/0/978/769.htm",
        "比亚迪王朝首款 D 级旗舰轿车，大汉实车曝光",
    )

    assert candidates[0]["url"] == (
        "https://img.ithome.com/newsuploadfiles/2026/7/car.jpg?x-bce-process=image/format,f_auto"
    )
    assert candidates[0]["status"] == "OK"
