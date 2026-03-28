import pytest
from pydantic import ValidationError

from video_agent.domain.review_workflow_models import ReviewDecision


def test_review_decision_requires_feedback_for_revise() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision(decision="revise", summary="needs update")


def test_review_decision_requires_feedback_for_repair() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision(decision="repair", summary="needs repair")


def test_review_decision_rejects_blank_feedback() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision(decision="revise", summary="needs update", feedback="   ")


def test_review_decision_accepts_confidence_between_zero_and_one() -> None:
    decision = ReviewDecision(
        decision="accept",
        summary="looks good",
        confidence=0.8,
    )

    assert decision.confidence == 0.8


def test_review_decision_rejects_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision(decision="accept", summary="looks good", confidence=1.1)


def test_review_decision_rejects_confidence_below_zero() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision(decision="accept", summary="looks good", confidence=-0.1)
