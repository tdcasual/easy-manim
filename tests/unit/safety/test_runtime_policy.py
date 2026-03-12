from video_agent.safety.runtime_policy import RuntimePolicy



def test_runtime_policy_rejects_non_whitelisted_paths(tmp_path) -> None:
    policy = RuntimePolicy(work_root=tmp_path)
    assert policy.is_allowed_write(tmp_path / "task" / "script.py") is True
    assert policy.is_allowed_write(tmp_path.parent / "escape.txt") is False
