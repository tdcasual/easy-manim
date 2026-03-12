from __future__ import annotations

import json
from pathlib import Path

from video_agent.evaluation.models import PromptSuite



def load_prompt_suite(path: Path | str, include_tags: set[str] | None = None) -> PromptSuite:
    suite = PromptSuite.model_validate(json.loads(Path(path).read_text()))
    seen: set[str] = set()
    filtered_cases = []
    for case in suite.cases:
        if case.case_id in seen:
            raise ValueError(f"Duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
        if include_tags is not None and not (include_tags & set(case.tags)):
            continue
        filtered_cases.append(case)
    return PromptSuite(suite_id=suite.suite_id, cases=filtered_cases)
