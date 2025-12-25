import logging
import sys


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format=(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "%(message)s | %(extra)s"
        ),
        force=True,
    )

    standard_attrs = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
    }

    class _ExtraFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.extra = {
                k: v
                for k, v in record.__dict__.items()
                if k not in standard_attrs and not k.startswith("_") and k != "extra"
            }
            return True

    root_logger = logging.getLogger()
    extra_filter = _ExtraFilter()
    for handler in root_logger.handlers:
        handler.addFilter(extra_filter)
