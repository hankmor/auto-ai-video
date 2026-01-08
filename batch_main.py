import argparse
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from util.logger import logger
from steps.batch.reader import BatchReader
from steps.batch.runner import BatchRunner


def main():
    parser = argparse.ArgumentParser(description="Batch AI Video Generator")
    parser.add_argument(
        "--file", "-f", type=str, required=True, help="Input CSV/Task file"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="batch_output",
        help="Output directory for logs and reports",
    )
    parser.add_argument(
        "--step",
        "-s",
        type=str,
        default="all",
        help="Step to run (script, image, animate, audio, video, all)",
    )
    args = parser.parse_args()

    # 1. Read Tasks
    reader = BatchReader()
    try:
        tasks = reader.read_tasks(args.file)
    except Exception as e:
        logger.error(f"Failed to load tasks: {e}")
        sys.exit(1)

    if not tasks:
        logger.warning("No tasks found in file.")
        sys.exit(0)

    # 2. Run Tasks
    runner = BatchRunner(output_dir=args.output, step_name=args.step)
    runner.run_tasks(tasks)


if __name__ == "__main__":
    main()
