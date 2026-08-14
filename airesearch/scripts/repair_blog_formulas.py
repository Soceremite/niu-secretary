#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from airesearch.blog_formula_repair import MathJaxBrowserCompiler, repair_blog_formulas
from airesearch.formula_ocr import FormulaOCRConfig, OpenAICompatibleFormulaOCRProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair compiler-confirmed blog formulas without regenerating the blog")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--paper-key", required=True)
    parser.add_argument("--force-retry", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=0.7)
    args = parser.parse_args()

    config = FormulaOCRConfig.from_env()
    provider = OpenAICompatibleFormulaOCRProvider(config) if config.configured else None
    result = repair_blog_formulas(
        args.db,
        args.paper_key,
        compiler=MathJaxBrowserCompiler(),
        provider=provider,
        min_confidence=args.min_confidence,
        force_retry=args.force_retry,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status in {"clean", "applied"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
