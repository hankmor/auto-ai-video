import csv
import os
from dataclasses import dataclass, field
from typing import List, Optional
from util.logger import logger

@dataclass
class BatchTask:
    topic: str
    category: str
    style: Optional[str] = None
    voice: Optional[str] = None
    enable_parallax: bool = False
    status: str = "pending"  # pending, running, success, failed
    error: str = ""
    task_id: str = field(init=False)

    def __post_init__(self):
        import hashlib
        # Create a unique ID based on content
        content = f"{self.topic}-{self.category}-{self.style}-{self.voice}"
        self.task_id = hashlib.md5(content.encode()).hexdigest()[:8]

class BatchReader:
    REQUIRED_HEADERS = {"topic", "category"}

    def read_tasks(self, file_path: str) -> List[BatchTask]:
        """
        Read tasks from a CSV file.
        
        CSV Format:
        topic,category,style,voice,enable_parallax
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Task file not found: {file_path}")

        tasks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Validate headers
                if not reader.fieldnames:
                    raise ValueError("CSV file is empty")
                
                headers = set(reader.fieldnames)
                missing = self.REQUIRED_HEADERS - headers
                if missing:
                    raise ValueError(f"Missing required headers: {missing}")

                for row in reader:
                    # Skip empty rows
                    if not row.get("topic") or not row.get("topic").strip():
                        continue

                    # Parse parallax boolean
                    parallax_str = row.get("enable_parallax", "").lower()
                    enable_parallax = parallax_str in ("true", "yes", "1", "on")

                    task = BatchTask(
                        topic=row["topic"].strip(),
                        category=row["category"].strip(),
                        style=row.get("style", "").strip() or None,
                        voice=row.get("voice", "").strip() or None,
                        enable_parallax=enable_parallax
                    )
                    tasks.append(task)
                    
            logger.info(f"📋 Loaded {len(tasks)} tasks from {file_path}")
            return tasks

        except Exception as e:
            logger.error(f"❌ Failed to read task file: {e}")
            raise
