from tests.integration.test_quality_score_alignment import (
    test_completed_eval_task_quality_score_aligns_runtime_learning_profile_and_eval as _test_completed_eval_alignment,
)
from tests.integration.test_quality_score_alignment import (
    test_profile_auto_apply_threshold_uses_scorecard_derived_median as _test_auto_apply_alignment,
)


def test_completed_eval_task_quality_score_aligns_runtime_learning_profile_and_eval(tmp_path) -> None:
    _test_completed_eval_alignment(tmp_path)


def test_profile_auto_apply_threshold_uses_scorecard_derived_median(tmp_path) -> None:
    _test_auto_apply_alignment(tmp_path)
