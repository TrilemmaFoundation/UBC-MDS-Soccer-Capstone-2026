"""Tests for football chatbot system prompt and scope (issue #96)."""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from src.chatbot.prompts import FOOTBALL_SYSTEM_PROMPT, SAMPLE_TEST_QUESTIONS


def _groq_api_key_configured() -> bool:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return bool(key) and key != "your_key_here"


def test_sample_questions_cover_core_research_questions():
    """Core deliverables RQ1–RQ3 (RQ4 match prediction is optional)."""
    rqs = {q["research_question"] for q in SAMPLE_TEST_QUESTIONS if q["research_question"]}
    assert rqs == {1, 2, 3}
    assert len(SAMPLE_TEST_QUESTIONS) == 3


def test_system_prompt_includes_dataset_and_research_context():
    prompt = FOOTBALL_SYSTEM_PROMPT.lower()
    for phrase in (
        "statsbomb",
        "is_international",
        "archetype",
        "mart_player_clusters",
        "mart_player_performance",
        "club vs national",
        "query_bigquery",
        "scope",
    ):
        assert phrase in prompt, f"Missing expected phrase: {phrase}"


def test_system_prompt_lists_competitions():
    prompt = FOOTBALL_SYSTEM_PROMPT
    for league in ("La Liga", "Premier League", "Bundesliga", "Champions League"):
        assert league in prompt


def _response_matches_keywords(text: str, keywords: list[str], min_hits: int = 1) -> bool:
    lowered = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in lowered)
    return hits >= min_hits


@pytest.mark.parametrize("case", SAMPLE_TEST_QUESTIONS, ids=lambda c: c["id"])
def test_keyword_relevance_heuristic(case):
    """Static check: each on-topic case has plausible answer keywords defined."""
    assert case["question"].strip()
    assert len(case["relevant_keywords"]) >= 3
    if case["expects_football_scope"]:
        assert case["research_question"] in (1, 2, 3)


@pytest.mark.skipif(
    not _groq_api_key_configured(),
    reason="GROQ_API_KEY not set in .env (or still placeholder)",
)
def test_live_responses_are_scoped():
    """Run all sample questions against Groq when API key is available."""
    from app.chatbot.llm_engine import ask_football_chatbot

    for case in SAMPLE_TEST_QUESTIONS:
        result = ask_football_chatbot(case["question"])
        answer = result.get("answer") if isinstance(result, dict) else result
        assert answer and isinstance(answer, str) and len(answer.strip()) > 20
        assert _response_matches_keywords(
            answer,
            case["relevant_keywords"],
            min_hits=2,
        ), f"Off-scope or weak answer for {case['id']}: {answer[:200]}"
