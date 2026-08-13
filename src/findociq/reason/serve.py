"""Launch a pinned Gemma AWQ tier with vLLM's OpenAI-compatible server."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from findociq.reason.generation import ModelTierConfig


def vllm_command(tier: ModelTierConfig, *, executable: str = sys.executable) -> tuple[str, ...]:
    """Build deterministic vLLM arguments from one reviewed model tier."""
    return (
        executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        tier.model_id,
        "--revision",
        tier.revision,
        "--served-model-name",
        tier.source_model_id,
        "--quantization",
        "awq",
        "--max-model-len",
        str(tier.max_model_length),
        "--gpu-memory-utilization",
        str(tier.gpu_memory_utilization),
        "--limit-mm-per-prompt",
        '{"image":1}',
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        type=Path,
        default=Path("configs/model_tiers/single_gpu.yaml"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    command = vllm_command(ModelTierConfig.from_yaml(args.tier))
    if args.dry_run:
        print(json.dumps(command))
        return
    subprocess.run(command, check=True)  # noqa: S603


if __name__ == "__main__":
    main()
