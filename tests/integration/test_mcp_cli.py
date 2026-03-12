import subprocess



def test_mcp_cli_help() -> None:
    completed = subprocess.run(
        ["python", "-m", "video_agent.server.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--transport" in completed.stdout
