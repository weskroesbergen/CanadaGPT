"""Progress tracking and logging utilities."""

import sys
from typing import Optional

from loguru import logger as _logger
from tqdm import tqdm


# Configure loguru logger
_logger.remove()  # Remove default handler
_logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# Add file logging with rotation
_logger.add(
    "logs/pipeline_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # New file at midnight
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
)

logger = _logger


class ProgressTracker:
    """Progress bar wrapper with logging integration."""

    def __init__(
        self,
        total: int,
        desc: str,
        unit: str = "items",
        leave: bool = True,
        disable: Optional[bool] = None,
    ):
        """
        Create progress bar with logging.

        Args:
            total: Total number of items to process
            desc: Description of the operation
            unit: Unit name (e.g., "MPs", "bills", "relationships")
            leave: Whether to keep progress bar after completion
            disable: Force disable progress bar (useful for non-TTY environments)
        """
        self.total = total
        self.desc = desc
        self.unit = unit

        logger.info(f"Starting: {desc} (total: {total:,} {unit})")

        self.pbar = tqdm(
            total=total,
            desc=desc,
            unit=unit,
            unit_scale=True,
            leave=leave,
            disable=disable,
            ncols=100,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
        )

    def update(self, n: int = 1) -> None:
        """Update progress bar by n items."""
        self.pbar.update(n)

    def set_postfix(self, **kwargs) -> None:
        """Set postfix text (e.g., current item name)."""
        self.pbar.set_postfix(kwargs)

    def close(self) -> None:
        """Close progress bar and log completion."""
        self.pbar.close()
        logger.info(f"Completed: {self.desc} ({self.total:,} {self.unit})")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Failed: {self.desc} - {exc_val}")
        self.close()
        return False  # Re-raise exception if any


def batch_iterator(items: list, batch_size: int, desc: str = "Processing"):
    """
    Iterate over items in batches with progress bar.

    Args:
        items: List of items to batch
        batch_size: Number of items per batch
        desc: Description for progress bar

    Yields:
        Batches of items (lists of size batch_size or smaller for last batch)
    """
    total_batches = (len(items) + batch_size - 1) // batch_size
    with ProgressTracker(total_batches, desc, unit="batches") as progress:
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            yield batch
            progress.update(1)
