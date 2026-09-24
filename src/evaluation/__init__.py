"""Evaluation metrics for structure detection and retrieval experiments."""

from src.evaluation.ground_truth import (
    build_qrel_candidates,
    join_clean_pages,
    validate_questions,
)
from src.evaluation.retrieval_metrics import (
    evaluate_retrieval,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)
from src.evaluation.structure_metrics import (
    render_structure_score,
    score_structure_review,
)

__all__ = [
    "build_qrel_candidates",
    "evaluate_retrieval",
    "join_clean_pages",
    "ndcg_at_k",
    "recall_at_k",
    "reciprocal_rank_at_k",
    "render_structure_score",
    "score_structure_review",
    "validate_questions",
]
