from video_agent.validation.static_check import StaticCheckValidator



def test_static_check_blocks_subprocess_usage() -> None:
    code = "import subprocess\nsubprocess.run(['rm', '-rf', '/'])"
    report = StaticCheckValidator().validate(code)
    assert report.passed is False
    assert report.issues[0].code == "forbidden_import"
