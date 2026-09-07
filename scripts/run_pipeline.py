"""
Main entry point to execute the ETL pipeline end to end.

Usage:
    python scripts/run_pipeline.py
    ETL_ENV=test python scripts/run_pipeline.py
"""
import json
import sys

from etl.orchestration.pipeline import run_pipeline
from etl.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    summary = run_pipeline()

    print("\n" + "=" * 60)
    print(f"Pipeline run: {summary['pipeline_run_id']}")
    print(f"Status: {summary['status']}")
    print("=" * 60)
    for step, counts in summary["steps"].items():
        print(f"  {step:22s} extracted={counts['extracted']:<5} loaded={counts['loaded']:<5} rejected={counts['rejected']}")

    if summary.get("quality_issues"):
        print(f"\nData quality issues ({len(summary['quality_issues'])}):")
        for issue in summary["quality_issues"]:
            print(f"  [{issue['severity']}] {issue['check']}: {issue['message']}")
    else:
        print("\nNo data quality issues found.")

    if summary["status"] == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
