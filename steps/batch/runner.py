import sys
import subprocess
import time
import os
import datetime
from typing import List
from util.logger import logger
from .reader import BatchTask


class BatchRunner:
    def __init__(self, output_dir: str = "batch_output", step_name: str = "all"):
        self.output_dir = output_dir
        self.step_name = step_name
        os.makedirs(output_dir, exist_ok=True)

    def run_tasks(self, tasks: List[BatchTask]):
        logger.info(f"🚀 Starting batch execution of {len(tasks)} tasks...")

        start_global = time.time()
        success_count = 0

        for i, task in enumerate(tasks):
            logger.info(f"▶️ [{i + 1}/{len(tasks)}] Processing: {task.topic}")
            task.status = "running"

            task_start_time = time.time()
            try:
                self._run_single_task(task)
                task.status = "success"
                success_count += 1
                logger.info(f"✅ Task {i + 1} completed successfully.")
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                logger.error(f"❌ Task {i + 1} failed: {e}")
            finally:
                duration = time.time() - task_start_time
                logger.info(f"⏱️ Task duration: {duration:.2f}s")

        total_duration = time.time() - start_global
        logger.info(
            f"🏁 Batch completed in {total_duration:.2f}s. Success: {success_count}/{len(tasks)}"
        )

        self._generate_report(tasks, total_duration)

    def _run_single_task(self, task: BatchTask):
        # Build command
        cmd = [
            sys.executable,
            "main.py",
            "--topic",
            task.topic,
            "--category",
            task.category,
            "--step",
            self.step_name,
            "--force",
        ]

        if task.style:
            cmd.extend(["--style", task.style])

        if task.voice:
            cmd.extend(["--voice", task.voice])

        # Explicitly set parallax based on task config
        if task.enable_parallax:
            cmd.extend(["--parallax", "true"])
        else:
            cmd.extend(["--parallax", "false"])

        # Create log file
        log_file = os.path.join(self.output_dir, f"task_{task.task_id}.log")
        logger.info(f"   📝 Log file: {log_file}")

        with open(log_file, "w") as f:
            # We redirect stdout/stderr to the log file to avoid cluttering main output
            # But we can also print to console if we want.
            # For batch, clean console is better.
            process = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                encoding="utf-8",
            )

        if process.returncode != 0:
            raise Exception(
                f"Process exited with code {process.returncode}. See {log_file} for details."
            )

    def _generate_report(self, tasks: List[BatchTask], total_duration: float):
        report_path = os.path.join(
            self.output_dir, f"batch_report_{int(time.time())}.md"
        )

        success_tasks = [t for t in tasks if t.status == "success"]
        failed_tasks = [t for t in tasks if t.status == "failed"]

        with open(report_path, "w") as f:
            f.write(f"# 📊 Batch Execution Report\n\n")
            f.write(
                f"- **Date**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"- **Total Duration**: {total_duration:.2f}s\n")
            f.write(f"- **Total Tasks**: {len(tasks)}\n")
            f.write(f"- **Success**: {len(success_tasks)}\n")
            f.write(f"- **Failed**: {len(failed_tasks)}\n\n")

            if failed_tasks:
                f.write("## ❌ Failed Tasks\n\n")
                f.write("| Topic | Category | Error | Log |\n")
                f.write("|---|---|---|---|\n")
                for t in failed_tasks:
                    log_link = f"task_{t.task_id}.log"
                    f.write(
                        f"| {t.topic} | {t.category} | {t.error} | [{log_link}]({log_link}) |\n"
                    )
                f.write("\n")

            f.write("## ✅ Task List\n\n")
            f.write("| Status | Topic | Category | Parallax | Voice | Style |\n")
            f.write("|---|---|---|---|---|---|\n")
            for t in tasks:
                status_icon = "✅" if t.status == "success" else "❌"
                f.write(
                    f"| {status_icon} | {t.topic} | {t.category} | {t.enable_parallax} | {t.voice or '-'} | {t.style or '-'} |\n"
                )

        logger.info(f"📄 Report generated: {report_path}")
