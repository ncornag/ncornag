#!/usr/bin/env python3
"""Plain-assert tests for exercise-media.py helpers. Run: python3 test-exercise-media.py"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "exercise_media", os.path.join(HERE, "exercise-media.py"))
em = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(em)


def test_normalize_tokens_lowercases_and_strips_punctuation():
    assert em.normalize_tokens("One-Arm Bent-Over Row") == {"one", "arm", "bent", "over", "row"}


def test_score_candidates_exact_match_scores_one():
    records = [{"id": "1", "name": "dead bug"}, {"id": "2", "name": "sit-up"}]
    scored = em.score_candidates("Dead Bug", records)
    assert scored[0]["id"] == "1"
    assert scored[0]["score"] == 1.0


def test_score_candidates_excludes_disjoint_names():
    records = [{"id": "1", "name": "dead bug"}, {"id": "2", "name": "barbell squat"}]
    scored = em.score_candidates("side plank", records)
    assert scored == []


def test_score_candidates_ranks_partial_overlap_below_exact():
    records = [
        {"id": "1", "name": "dumbbell single leg calf raise"},
        {"id": "2", "name": "single leg calf raise"},
    ]
    scored = em.score_candidates("Single-Leg Calf Raise", records)
    assert scored[0]["id"] == "2"
    assert scored[0]["score"] == 1.0
    assert scored[1]["id"] == "1"
    assert scored[1]["score"] < 1.0


def test_slugify_kebab_cases_the_name():
    assert em.slugify("Dead Bug") == "dead-bug"
    assert em.slugify("One-Arm Bent-Over Row") == "one-arm-bent-over-row"


if __name__ == "__main__":
    test_normalize_tokens_lowercases_and_strips_punctuation()
    test_score_candidates_exact_match_scores_one()
    test_score_candidates_excludes_disjoint_names()
    test_score_candidates_ranks_partial_overlap_below_exact()
    test_slugify_kebab_cases_the_name()
    print("OK")
