from pathlib import Path

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
