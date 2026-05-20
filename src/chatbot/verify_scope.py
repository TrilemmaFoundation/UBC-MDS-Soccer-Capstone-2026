#!/usr/bin/env python3
"""
Usage (from repo root):
    python -m src.chatbot.verify_scope

Requires GROQ_API_KEY in the environment for live LLM calls.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from src.chatbot.prompts import SAMPLE_TEST_QUESTIONS


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [kw for kw in keywords if kw.lower() in lowered]


def main() -> int:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key.strip() in ("", "your_key_here"):
        print("GROQ_API_KEY not set (or still placeholder) — skipping live LLM verification.")
        print(f"Add a real key to {REPO_ROOT / '.env'} or export GROQ_API_KEY in your shell.")
        print(f"Defined {len(SAMPLE_TEST_QUESTIONS)} sample questions:")
        for case in SAMPLE_TEST_QUESTIONS:
            rq = case["research_question"] or "scope"
            print(f"  [{rq}] {case['question'][:70]}...")
        return 0

    from app.chatbot.llm_engine import ask_football_chatbot

    passed = 0
    for case in SAMPLE_TEST_QUESTIONS:
        print(f"\n=== {case['id']} (RQ{case['research_question'] or 'scope'}) ===")
        print(f"Q: {case['question']}\n")
        answer = ask_football_chatbot(case["question"])
        hits = _keyword_hits(answer, case["relevant_keywords"])
        ok = len(hits) >= (2 if case["expects_football_scope"] else 1)
        status = "PASS" if ok else "REVIEW"
        if ok:
            passed += 1
        print(f"A: {answer}\n")
        print(f"{status} — keyword hits: {hits or '(none)'}")

    print(f"\n{passed}/{len(SAMPLE_TEST_QUESTIONS)} checks passed.")
    return 0 if passed == len(SAMPLE_TEST_QUESTIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
