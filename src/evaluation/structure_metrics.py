"""Metrics for manual review of detected rhetorical boundaries."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


VALID_STATUSES = {"exact", "near", "missed", "false_positive", "not_applicable"}
REQUIRED_TOLERANT_LABELS = {
    "identitas_terdakwa",
    "fakta",
    "pertimbangan_hukum",
    "penutup",
}


def score_structure_review(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Score completed review rows and evaluate the milestone criteria."""
    normalized = [dict(row) for row in rows]
    reviewed = [row for row in normalized if str(row.get("review_status", "")).strip()]
    invalid = sorted(
        {
            str(row.get("review_status", "")).strip()
            for row in reviewed
            if str(row.get("review_status", "")).strip() not in VALID_STATUSES
        }
    )
    if invalid:
        raise ValueError(f"Invalid review_status value(s): {', '.join(invalid)}")

    for row in reviewed:
        gold_present = str(row.get("gold_present", "")).strip().lower()
        if gold_present not in {"yes", "no"}:
            raise ValueError(
                "Every reviewed row must set gold_present to yes or no: "
                f"{row.get('document_id')} / {row.get('section_label')}"
            )
        status = str(row["review_status"]).strip()
        if status in {"exact", "near", "missed"} and gold_present != "yes":
            raise ValueError(f"Status {status} requires gold_present=yes")
        if status == "not_applicable" and gold_present != "no":
            raise ValueError("Status not_applicable requires gold_present=no")
        detected = str(row.get("detected", "")).strip().lower()
        if detected not in {"yes", "no"}:
            raise ValueError("Every reviewed row must set detected to yes or no")
        if status in {"exact", "near", "false_positive"} and detected != "yes":
            raise ValueError(f"Status {status} requires detected=yes")
        if status in {"missed", "not_applicable"} and detected != "no":
            raise ValueError(f"Status {status} requires detected=no")

    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reviewed:
        by_label[str(row.get("section_label", ""))].append(row)

    per_label = {
        label: _score_label(label_rows)
        for label, label_rows in sorted(by_label.items())
    }
    complete = len(reviewed) == len(normalized) and bool(normalized)
    acceptance = _acceptance(per_label) if complete else None
    return {
        "total_rows": len(normalized),
        "reviewed_rows": len(reviewed),
        "completion": len(reviewed) / len(normalized) if normalized else 0.0,
        "complete": complete,
        "per_label": per_label,
        "acceptance": acceptance,
    }


def render_structure_score(score: Mapping[str, Any]) -> str:
    """Render structure-review metrics as a compact Markdown report."""
    lines = [
        "# Audit manual batas struktur",
        "",
        f"Review selesai: {score['reviewed_rows']}/{score['total_rows']} "
        f"({score['completion']:.1%})",
        "",
        "| Label | Gold | Prediksi | Exact P/R | Toleran P/R | Missed | False positive |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, row in score["per_label"].items():
        lines.append(
            f"| `{label}` | {row['gold_positive']} | {row['predicted_positive']} | "
            f"{_format_ratio(row['exact_precision'])}/{_format_ratio(row['exact_recall'])} | "
            f"{_format_ratio(row['tolerant_precision'])}/{_format_ratio(row['tolerant_recall'])} | "
            f"{row['missed']} | {row['false_positive']} |"
        )
    lines.append("")
    if score["acceptance"] is None:
        lines.append("Target diagnostik belum dinilai karena audit manual belum lengkap.")
    elif score["acceptance"]["passed"]:
        lines.append("Target diagnostik: **LULUS**.")
    else:
        lines.append("Target diagnostik: **BELUM LULUS**.")
        lines.extend(f"- {reason}" for reason in score["acceptance"]["reasons"])
    lines.append("")
    return "\n".join(lines)


def _score_label(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold_positive = sum(str(row["gold_present"]).strip().lower() == "yes" for row in rows)
    predicted_positive = sum(str(row.get("detected", "")).strip().lower() == "yes" for row in rows)
    statuses = [str(row["review_status"]).strip() for row in rows]
    exact = statuses.count("exact")
    near = statuses.count("near")
    tolerant = exact + near
    return {
        "reviewed": len(rows),
        "gold_positive": gold_positive,
        "predicted_positive": predicted_positive,
        "exact": exact,
        "near": near,
        "missed": statuses.count("missed"),
        "false_positive": statuses.count("false_positive"),
        "not_applicable": statuses.count("not_applicable"),
        "exact_precision": _divide(exact, predicted_positive),
        "exact_recall": _divide(exact, gold_positive),
        "tolerant_precision": _divide(tolerant, predicted_positive),
        "tolerant_recall": _divide(tolerant, gold_positive),
    }


def _acceptance(per_label: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    amar = per_label.get("amar_putusan")
    if not amar or amar["exact_recall"] != 1.0:
        reasons.append("Exact recall `amar_putusan` harus 100%.")
    for label in sorted(REQUIRED_TOLERANT_LABELS):
        result = per_label.get(label)
        if not result or result["tolerant_recall"] is None or result["tolerant_recall"] < 0.90:
            reasons.append(f"Tolerant recall `{label}` harus minimal 90%.")
    for label in ("amar_putusan", "pertimbangan_hukum"):
        result = per_label.get(label)
        if result and result["false_positive"]:
            reasons.append(f"`{label}` tidak boleh memiliki false positive.")
    return {"passed": not reasons, "reasons": reasons}


def _divide(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _format_ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"
