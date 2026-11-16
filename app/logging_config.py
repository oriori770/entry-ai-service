import logging
import sys
from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(level: int = logging.INFO) -> None:
    """Configures colorful Rich logging for the application."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=True,
                show_path=False,
                markup=True,
            )
        ],
        force=True,
    )

    # Tone down noisy external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
