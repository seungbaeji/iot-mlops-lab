import logging
import logging.config
import tomllib
from pathlib import Path


def setup_logger(config_path: str) -> None:
    logger = logging.getLogger(__name__)
    with open(config_path, "rb") as f:
        logging_config = tomllib.load(f)

    file_handler = logging_config.get("handlers", {}).get("file")
    try:
        log_file = file_handler.get("filename") if file_handler else None
        log_path = Path(log_file) if log_file else None
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        parent_dir = log_path.parent if log_path else "N/A"
        logger.error(f"Failed to create log directory {parent_dir}: {e}")

    logging.config.dictConfig(logging_config)
    logger.info("Logger configuration is applied.")
