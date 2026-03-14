from __future__ import annotations

import json
from pathlib import Path

from video_agent.evaluation.models import PromptSuite



def load_prompt_suite(
    path: Path | str,
    include_tags: set[str] | None = None,
    match_all_tags: bool = False,
) -> PromptSuite:
    suite = PromptSuite.model_validate(json.loads(Path(path).read_text()))
    seen: set[str] = set()
    filtered_cases = []
    for case in suite.cases:
        if case.case_id in seen:
            raise ValueError(f"Duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
        case_tags = set(case.tags)
        if include_tags is not None and not _matches_include_tags(case_tags, include_tags, match_all_tags):
            continue
        filtered_cases.append(case)
    return PromptSuite(suite_id=suite.suite_id, cases=filtered_cases)


def _matches_include_tags(case_tags: set[str], include_tags: set[str], match_all_tags: bool) -> bool:
    if match_all_tags:
        return include_tags.issubset(case_tags)
    return bool(include_tags & case_tags)
