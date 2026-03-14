from pathlib import Path

import pytest

from video_agent.evaluation.corpus import load_prompt_suite



def test_load_prompt_suite_returns_cases() -> None:
    suite = load_prompt_suite(Path("evals/beta_prompt_suite.json"))

    assert suite.suite_id == "beta-prompt-suite"
    assert len(suite.cases) >= 3
    assert {case.case_id for case in suite.cases}



def test_load_prompt_suite_can_filter_by_tag(tmp_path: Path) -> None:
    fixture = tmp_path / "suite.json"
    fixture.write_text(
        '{"suite_id":"demo","cases":['
        '{"case_id":"a","prompt":"draw a circle","tags":["smoke"]},'
        '{"case_id":"b","prompt":"draw a square","tags":["real-provider"]}'
        ']}'
    )

    suite = load_prompt_suite(fixture, include_tags={"smoke"})

    assert [case.case_id for case in suite.cases] == ["a"]


def test_load_prompt_suite_can_require_all_tags(tmp_path: Path) -> None:
    fixture = tmp_path / "suite.json"
    fixture.write_text(
        '{"suite_id":"demo","cases":['
        '{"case_id":"a","prompt":"draw a circle","tags":["quality"]},'
        '{"case_id":"b","prompt":"draw a square","tags":["real-provider"]},'
        '{"case_id":"c","prompt":"draw a triangle","tags":["real-provider","quality"]}'
        ']}'
    )

    suite = load_prompt_suite(fixture, include_tags={"real-provider", "quality"}, match_all_tags=True)

    assert [case.case_id for case in suite.cases] == ["c"]


def test_official_suite_has_multiple_real_provider_quality_cases() -> None:
    suite = load_prompt_suite(
        Path("evals/beta_prompt_suite.json"),
        include_tags={"real-provider", "quality"},
        match_all_tags=True,
    )

    assert len(suite.cases) >= 15


def test_load_prompt_suite_preserves_live_case_metadata(tmp_path: Path) -> None:
    fixture = tmp_path / "suite.json"
    fixture.write_text(
        """
        {
          "suite_id": "live-demo",
          "cases": [
            {
              "case_id": "formula-live",
              "prompt": "show the quadratic formula",
              "tags": ["real-provider", "quality", "mathtex"],
              "risk_domains": ["formula", "layout"],
              "review_focus": ["formula legibility", "term emphasis"],
              "baseline_group": "live-rc-core",
              "manual_review_required": true
            }
          ]
        }
        """
    )

    suite = load_prompt_suite(fixture)

    case = suite.cases[0]
    assert case.risk_domains == ["formula", "layout"]
    assert case.review_focus == ["formula legibility", "term emphasis"]
    assert case.baseline_group == "live-rc-core"
    assert case.manual_review_required is True


def test_load_prompt_suite_rejects_unknown_risk_domains(tmp_path: Path) -> None:
    fixture = tmp_path / "suite.json"
    fixture.write_text(
        """
        {
          "suite_id": "live-demo",
          "cases": [
            {
              "case_id": "bad-risk",
              "prompt": "draw a circle",
              "tags": ["real-provider"],
              "risk_domains": ["made-up-domain"]
            }
          ]
        }
        """
    )

    with pytest.raises(ValueError, match="unknown risk_domains"):
        load_prompt_suite(fixture)
