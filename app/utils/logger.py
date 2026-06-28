"""Structured JSON logger for the Deep Agent application."""

import logging
import json
import time
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_obj.update(record.extra)
        return json.dumps(log_obj)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(JSONFormatter())
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8")
    fh.setFormatter(JSONFormatter())
    logger.addHandler(fh)

    return logger


def log_request(logger: logging.Logger, question: str, intent: str, tools: list,
                exec_time: float, pdf_chunks: int = 0, error: str = None):
    extra = {
        "user_question": question,
        "intent": intent,
        "tools_selected": tools,
        "execution_time_ms": round(exec_time * 1000, 2),
        "pdf_chunks_retrieved": pdf_chunks,
    }
    if error:
        extra["error"] = error
    logger.info("request_processed", extra={"extra": extra})
