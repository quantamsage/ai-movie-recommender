import json

import pytest

import ai
from ai import (
    RecommendationError,
    build_prompt,
    build_similar_request,
    get_recommendations,
    parse_json,
    validate_movie,
    validate_recommendations,
)


def movie(title="Arrival", year=2016, score=90, **extra):
    m = {
        "title": title, "year": year, "genre": "Sci-Fi", "description": "A linguist meets aliens.",
        "why_recommended": "Thoughtful sci-fi.", "match_score": score,
    }
    m.update(extra)
    return m


def test_parse_json_recovers_from_fences_and_chatter():
    payload = {"recommendations": [movie()]}
    assert parse_json(f"```json\n{json.dumps(payload)}\n```") == payload
    assert parse_json(f"Here you go: {json.dumps(payload)} enjoy") == payload
    with pytest.raises(RecommendationError):
        parse_json("nope")


def test_validate_movie_cleans_numbers_and_rejects_bad_items():
    cleaned = validate_movie(movie(year="2016", score="140%"))
    assert cleaned["year"] == 2016 and cleaned["match_score"] == 100
    assert validate_movie(movie(year=1700)) is None
    assert validate_movie(movie(title="  ")) is None
    assert validate_movie("not a dict") is None


def test_validate_recommendations_filters_sorts_and_excludes():
    data = {"recommendations": [
        movie("Low", score=40), movie("High", score=95), movie("high", score=10),  # duplicate title
        movie("Old", year=1950), movie("Seen", score=99),
    ]}
    result = validate_recommendations(data, 5, min_year=2000, exclude_titles=["seen"])
    assert [m["title"] for m in result] == ["High", "Low"]


def test_validate_recommendations_errors_when_nothing_usable():
    with pytest.raises(RecommendationError):
        validate_recommendations({"recommendations": [movie(year=1700)]}, 3)
    with pytest.raises(RecommendationError):
        validate_recommendations({"oops": []}, 3)


def test_prompt_lists_exclusions_and_filters():
    prompt = build_prompt("cozy", 3, "Comedy", 2000, 2010, exclude_titles=["Up", "Elf"])
    assert "Elf; Up" in prompt and "Comedy" in prompt and "between 2000 and 2010" in prompt
    assert "Do not recommend" not in build_prompt("cozy", 3, "Any", None, None)


def test_more_like_this_flow(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test-key")
    captured = {}

    def fake_call(prompt, api_key):
        captured["prompt"] = prompt
        return json.dumps({"recommendations": [movie("Arrival"), movie("Contact", 1997, 88)]})

    monkeypatch.setattr(ai, "call_ai", fake_call)
    seed = movie("Arrival")
    result = get_recommendations(build_similar_request(seed), count=3, exclude_titles=["Arrival"])
    assert [m["title"] for m in result] == ["Contact"]       # seed movie filtered out
    assert "Movies similar to Arrival (2016)" in captured["prompt"]


def test_missing_key_gives_friendly_error(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "your_api_key_here")
    with pytest.raises(RecommendationError, match="No API key"):
        get_recommendations("anything")
