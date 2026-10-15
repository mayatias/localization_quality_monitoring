import argparse
import json
from pathlib import Path
from .config import recording_count, seed
from .dataset_generation import make_dataset
from .pipeline import load_thresholds, process_file
from .data_storage import write_results
from .evaluation import evaluate

def main() -> None:
    parser = argparse.ArgumentParser(description="Vehicle location quality monitoring")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate", help="Generate reproducible sample drives")
    generate.add_argument("--count", type=int, default=recording_count)
    generate.add_argument("--seed", type=int, default=seed)
    generate.add_argument("--raw", type=Path, default=Path("data/raw"))
    generate.add_argument("--truth", type=Path, default=Path("data/ground_truth"))
    run = sub.add_parser("run", help="Process JSON drives and write warehouse outputs")
    run.add_argument("--raw", type=Path, default=Path("data/raw"))
    run.add_argument("--truth", type=Path, default=Path("data/ground_truth"))
    run.add_argument("--output", type=Path, default=Path("data/processed"))
    run.add_argument("--db", type=Path, default=Path("data/quality.duckdb"))
    run.add_argument("--thresholds", type=Path, default=Path("src/thresholds.json"))
    args = parser.parse_args()
    if args.command == "generate":
        if args.count < 0:
            parser.error("--count must be nonnegative")
        paths = make_dataset(args.raw, args.truth, args.count, args.seed)
        print(f"Generated {len(paths)} drives in {args.raw}; ground truth in {args.truth}")
        return
    thresholds = load_thresholds(args.thresholds)
    paths = sorted(args.raw.glob("*.json"))
    results = [process_file(path, thresholds) for path in paths]
    write_results(results, args.output, args.db)
    print(json.dumps({"drives": len(results), "events": sum(len(r['events']) for r in results),
        "evaluation": evaluate(results, args.truth), "duckdb": str(args.db), "parquet_dir": str(args.output)}, indent=2))

if __name__ == "__main__":
    main()