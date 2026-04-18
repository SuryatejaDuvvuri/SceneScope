#!/usr/bin/env python3
import argparse
import json
import statistics
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.scenePlanner import plan_scene_to_shot, parse_refinement_intent  # noqa: E402


def _subject_recall(expected: list[str], predicted: list[str]) -> float:
    exp = {s.upper().strip() for s in expected if s and s.strip()}
    if not exp:
        return 1.0
    got = {s.upper().strip() for s in predicted if s and s.strip()}
    return len(exp & got) / len(exp)


def _population_match(expected: str, ambient_hint: str | None) -> float:
    if not expected:
        return 1.0
    hint = (ambient_hint or "").lower()
    if expected == "crowded":
        return 1.0 if any(k in hint for k in ("extras", "crowd", "patrons", "students", "bystanders", "populated")) else 0.0
    if expected == "sparse":
        return 1.0 if any(k in hint for k in ("sparse", "empty", "isolated")) else 0.0
    return 0.0


def _directive_completeness(plan) -> float:
    fields = [
        plan.setting_direction,
        plan.camera_direction,
        plan.blocking_direction,
        plan.lighting_direction,
    ]
    present = sum(1 for f in fields if (f or "").strip())
    return present / 4


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SceneScope shot planner and refinement intent parser.")
    parser.add_argument(
        "--dataset",
        default=str(BACKEND_ROOT / "training" / "benchmark_scene_planner.json"),
        help="Path to benchmark dataset JSON.",
    )
    args = parser.parse_args()

    data_path = Path(args.dataset)
    dataset = json.loads(data_path.read_text())

    subject_scores: list[float] = []
    population_scores: list[float] = []
    directive_scores: list[float] = []
    intent_confidences: list[float] = []

    print(f"Loaded {len(dataset)} benchmark scenes from {data_path}")
    for sample in dataset:
        plan = plan_scene_to_shot(
            heading=sample["heading"],
            description=sample["description"],
            mood=sample["mood"],
            visual_summary=sample.get("visual_summary", ""),
            dialogue_lines=sample.get("dialogue_lines", []),
            time_period=sample.get("time_period"),
            tone=sample.get("tone"),
        )

        feedback = "Keep character identity and setting continuity, but make lighting moodier."
        intent = parse_refinement_intent(
            heading=sample["heading"],
            description=sample["description"],
            feedback=feedback,
            answers={"Lighting preference?": "darker with stronger contrast"},
        )

        s_score = _subject_recall(sample.get("expected_required_subjects", []), plan.required_subjects)
        p_score = _population_match(sample.get("expected_population", ""), plan.ambient_population_hint)
        d_score = _directive_completeness(plan)

        subject_scores.append(s_score)
        population_scores.append(p_score)
        directive_scores.append(d_score)
        intent_confidences.append(intent.confidence)

        print(
            f"[{sample['id']}] subjects={s_score:.2f} population={p_score:.2f} directives={d_score:.2f} "
            f"intent_priority={intent.priority} intent_conf={intent.confidence:.2f}"
        )

    print("\n=== Aggregate ===")
    print(f"subject_recall_avg: {statistics.mean(subject_scores):.3f}")
    print(f"population_hint_match_avg: {statistics.mean(population_scores):.3f}")
    print(f"directive_completeness_avg: {statistics.mean(directive_scores):.3f}")
    print(f"intent_confidence_avg: {statistics.mean(intent_confidences):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
