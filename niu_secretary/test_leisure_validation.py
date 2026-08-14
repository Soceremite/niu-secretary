from datetime import date
import json

from niu_secretary.leisure_validation import validate_leisure_data_dir


def test_strict_content_rejects_generic_search_url(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "context.json").write_text(
        json.dumps(
            {
                "generated": "2026-06-19T12:00:00+08:00",
                "schedule": {},
                "fitness": {},
                "moodProfile": {},
                "dailyNote": "note",
                "recommendationStrategy": {},
            }
        ),
        encoding="utf-8",
    )
    (data / "movies.json").write_text(
        json.dumps(
            [
                {
                    "id": "movie-001",
                    "title": "影片",
                    "reason": "推荐理由",
                    "matchScore": 90,
                    "doubanUrl": "https://movie.douban.com/search?q=test",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = validate_leisure_data_dir(data, strict_content=True, today=date(2026, 6, 19))

    assert result["status"] == "failed"
    assert any("invalid doubanUrl" in error for error in result["errors"])


def test_strict_content_accepts_valid_recommendation(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "context.json").write_text(
        json.dumps(
            {
                "generated": "2026-06-19T12:00:00+08:00",
                "schedule": {},
                "fitness": {},
                "moodProfile": {},
                "dailyNote": "note",
                "recommendationStrategy": {},
            }
        ),
        encoding="utf-8",
    )
    (data / "music.json").write_text(
        json.dumps(
            [
                {
                    "id": "music-001",
                    "title": "歌单",
                    "reason": "推荐理由",
                    "matchScore": 90,
                    "platformUrl": "https://music.example.com/playlist/123",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = validate_leisure_data_dir(data, strict_content=True, today=date(2026, 6, 19))

    assert result == {"status": "passed", "checked": ["context.json", "music.json"], "errors": []}


def test_strict_content_rejects_movie_without_subject_id_and_cover(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "context.json").write_text(
        json.dumps(
            {
                "generated": "2026-06-19T12:00:00+08:00",
                "schedule": {},
                "fitness": {},
                "moodProfile": {},
                "dailyNote": "note",
                "recommendationStrategy": {},
            }
        ),
        encoding="utf-8",
    )
    (data / "movies.json").write_text(
        json.dumps(
            [
                {
                    "id": "movie-001",
                    "title": "影片",
                    "reason": "推荐理由",
                    "matchScore": 90,
                    "doubanUrl": "https://movie.douban.com/subject/",
                    "coverUrl": "",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = validate_leisure_data_dir(data, strict_content=True, today=date(2026, 6, 19))

    assert result["status"] == "failed"
    assert any("invalid doubanUrl" in error for error in result["errors"])
    assert any("all movie coverUrl values are empty" in error for error in result["errors"])


def test_strict_content_accepts_hash_route_detail_url(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "context.json").write_text(
        json.dumps(
            {
                "generated": "2026-06-19T12:00:00+08:00",
                "schedule": {},
                "fitness": {},
                "moodProfile": {},
                "dailyNote": "note",
                "recommendationStrategy": {},
            }
        ),
        encoding="utf-8",
    )
    (data / "podcasts.json").write_text(
        json.dumps(
            [
                {
                    "id": "podcast-001",
                    "title": "播客",
                    "reason": "推荐理由",
                    "matchScore": 88,
                    "platformUrl": "https://music.163.com/#/djradio?id=792000000",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = validate_leisure_data_dir(data, strict_content=True, today=date(2026, 6, 19))

    assert result["status"] == "passed"
