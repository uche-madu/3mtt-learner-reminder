# logging.py
import os
import sys
import json
import contextvars
import uuid
from loguru import logger as _logger

# Ensure log directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ContextVar to store request-specific data, e.g., request_id
_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def set_request_id(request_id: str) -> None:
    """Set the current request_id in the ContextVar."""
    _request_id_ctx.set(request_id)


def clear_request_id() -> None:
    """Clear the request_id from the ContextVar."""
    _request_id_ctx.set(None)


def get_request_id() -> str | None:
    """Get the current request_id from the ContextVar."""
    return _request_id_ctx.get()


def _json_sink(message) -> None:
    """Custom sink for loguru that outputs structured JSON with request_id + extras."""
    record = message.record
    # Always try ContextVar first, fallback to generated UUID
    rid = get_request_id() or str(uuid.uuid4())

    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "function": record["function"],
        "module": record["module"],
        "line": record["line"],
        "request_id": rid,
    }

    if record["exception"]:
        log_entry["exception"] = {
            "type": record["exception"].type.__name__,
            "message": str(record["exception"].value),
            "traceback": record["exception"].traceback,
        }

    # Merge extra fields, but don't allow them to override request_id
    for k, v in record["extra"].items():
        if k == "request_id":
            continue
        log_entry[k] = v

    print(json.dumps(log_entry), file=sys.stdout)


def setup_logging(log_to_file: bool = True) -> None:
    """
    Configure the global logger instance.

    - Removes default logger.
    - Adds a JSON sink that includes request_id from ContextVar.
    - Optionally logs to a rotating file.
    - Enables backtrace and diagnose for detailed exceptions.
    """
    _logger.remove()  # Remove default sink
    # Console / stdout sink
    _logger.add(_json_sink, level="DEBUG", backtrace=True, diagnose=True)

    if log_to_file:
        _logger.add(
            os.path.join(LOG_DIR, "app.log"),
            rotation="10 MB",  # Rotate after 10 MB
            retention="7 days",  # Keep 7 days of logs
            level="INFO",
            serialize=True,  # JSON format
        )


# Expose logger to import everywhere in the app
logger = _logger
