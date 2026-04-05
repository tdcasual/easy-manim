import subprocess
import sys


def test_api_main_build_parser_does_not_require_uvicorn() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import builtins\n"
                "real_import = builtins.__import__\n"
                "def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):\n"
                "    if name == 'uvicorn' or name.startswith('uvicorn.'):\n"
                "        raise ModuleNotFoundError('simulated missing uvicorn')\n"
                "    return real_import(name, globals, locals, fromlist, level)\n"
                "builtins.__import__ = guarded_import\n"
                "import video_agent.server.api_main as module\n"
                "parser = module.build_api_parser()\n"
                "assert parser is not None\n"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_beta_smoke_helpers_import_without_mcp_runtime() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import builtins\n"
                "real_import = builtins.__import__\n"
                "def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):\n"
                "    if name == 'mcp' or name.startswith('mcp.'):\n"
                "        raise ModuleNotFoundError('simulated missing mcp')\n"
                "    return real_import(name, globals, locals, fromlist, level)\n"
                "builtins.__import__ = guarded_import\n"
                "import scripts.beta_smoke as module\n"
                "assert str(module.repo_root()).endswith('easy-manim')\n"
                "assert module.build_parser() is not None\n"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
