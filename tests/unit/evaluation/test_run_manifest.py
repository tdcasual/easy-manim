from pathlib import Path

from video_agent.evaluation.run_manifest import EvalCaseState, EvalRunManifest


def test_run_manifest_round_trips_case_state(tmp_path: Path) -> None:
    manifest = EvalRunManifest(
        run_id="run-123",
        suite_id="demo",
        provider="stub",
        include_tags=["quality"],
        match_all_tags=True,
        cases={
            "case-a": EvalCaseState(
                status="completed",
                root_task_id="task-1",
                terminal_task_id="task-1",
                issue_codes=["near_blank_preview"],
                attempt_count=1,
            ),
        },
    )

    path = tmp_path / "run.json"
    path.write_text(manifest.model_dump_json(indent=2))
    restored = EvalRunManifest.model_validate_json(path.read_text())

    assert restored.cases["case-a"].status == "completed"
    assert restored.cases["case-a"].root_task_id == "task-1"
    assert restored.cases["case-a"].attempt_count == 1
