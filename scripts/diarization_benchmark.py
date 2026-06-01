#!/usr/bin/env python3
"""Benchmark and compare diarization outputs across models."""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

from pyannote.audio import Pipeline

from backend.app.config.settings import Settings


COMPARISON_METRICS = (
    "segment_count",
    "speaker_count",
    "total_speech_duration",
    "mean_segment_duration",
    "median_segment_duration",
)


def _safe_slug(value: str) -> str:
    return value.replace("/", "__").replace(":", "_")


def _build_segments(annotation) -> List[Dict]:
    segments: List[Dict] = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append(
            {
                "speaker": str(speaker),
                "start": float(turn.start),
                "end": float(turn.end),
            }
        )

    segments.sort(key=lambda item: (item["start"], item["end"], item["speaker"]))
    return segments


def _summarize_segments(segments: List[Dict]) -> Dict:
    durations: List[float] = []
    speaker_durations: Dict[str, float] = {}
    total_duration = 0.0

    for segment in segments:
        duration = max(0.0, segment["end"] - segment["start"])
        durations.append(duration)
        total_duration += duration
        speaker = segment["speaker"]
        speaker_durations[speaker] = speaker_durations.get(speaker, 0.0) + duration

    durations.sort()
    count = len(durations)
    if count == 0:
        median_duration = 0.0
    elif count % 2 == 1:
        median_duration = durations[count // 2]
    else:
        median_duration = (durations[count // 2 - 1] + durations[count // 2]) / 2.0

    mean_duration = total_duration / count if count else 0.0
    return {
        "segment_count": len(segments),
        "speaker_count": len(speaker_durations),
        "total_speech_duration": total_duration,
        "mean_segment_duration": mean_duration,
        "median_segment_duration": median_duration,
        "speaker_durations": speaker_durations,
    }


def _load_pipeline(model_name: str, token: str, device: str) -> Pipeline:
    pipeline = Pipeline.from_pretrained(model_name, token=token)
    try:
        pipeline.to(device)
    except Exception:
        print(f"Warning: unable to move pipeline '{model_name}' to {device}")
    return pipeline


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _compare_summaries(
    summaries: Dict[str, Dict], baseline_model: str
) -> Dict:
    baseline = summaries[baseline_model]
    deltas: Dict[str, Dict[str, float]] = {}

    for metric in COMPARISON_METRICS:
        baseline_value = float(baseline.get(metric, 0.0))
        deltas[metric] = {
            model: float(summary.get(metric, 0.0)) - baseline_value
            for model, summary in summaries.items()
            if model != baseline_model
        }

    return {
        "baseline": baseline_model,
        "metrics": summaries,
        "deltas": deltas,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark and compare diarization outputs."
    )
    parser.add_argument(
        "audio",
        nargs="+",
        help="Audio file(s) to diarize.",
    )
    parser.add_argument(
        "--model",
        dest="models",
        action="append",
        help="Hugging Face diarization model id (repeatable).",
    )
    parser.add_argument(
        "--output-dir",
        default="temp/diarization_bench",
        help="Directory for JSON outputs.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("HF_TOKEN"),
        help="Hugging Face token (defaults to HF_TOKEN).",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Torch device for pipeline execution.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = Settings()

    models = args.models or [settings.DIARIZATION_MODEL]
    token = args.token or settings.HF_TOKEN
    if not token:
        print("HF_TOKEN is required for diarization benchmarking")
        return 1

    pipelines = {
        model: _load_pipeline(model, token, args.device) for model in models
    }
    output_dir = Path(args.output_dir)

    for audio in args.audio:
        audio_path = Path(audio)
        if not audio_path.exists():
            print(f"Missing audio file: {audio_path}")
            continue

        summaries: Dict[str, Dict] = {}
        for model, pipeline in pipelines.items():
            diarization = pipeline(str(audio_path))
            annotation = getattr(diarization, "speaker_diarization", diarization)
            segments = _build_segments(annotation)
            summary = _summarize_segments(segments)
            summary["model"] = model
            summary["audio"] = str(audio_path)
            summaries[model] = summary

            model_slug = _safe_slug(model)
            segments_path = output_dir / f"{audio_path.stem}__{model_slug}__segments.json"
            summary_path = output_dir / f"{audio_path.stem}__{model_slug}__summary.json"
            _write_json(segments_path, {"audio": str(audio_path), "segments": segments})
            _write_json(summary_path, summary)
            print(
                f"{audio_path.name} | {model}: "
                f"{summary['speaker_count']} speakers, "
                f"{summary['segment_count']} segments"
            )

        if len(models) > 1 and summaries:
            comparison = _compare_summaries(summaries, models[0])
            comparison_path = output_dir / f"{audio_path.stem}__comparison.json"
            _write_json(comparison_path, comparison)
            print(
                f"Comparison saved: {comparison_path} (baseline: {models[0]})"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
