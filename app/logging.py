import logging
import json

class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON strings.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.name,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        return json.dumps(log_record)

def setup_logging(level=logging.INFO):
    """
    Configures the root logger to use the JsonFormatter.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a new handler and set the formatter
    handler = logging.StreamHandler()
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

if __name__ == "__main__":
    setup_logging()
    logging.info("Logging configured successfully.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
