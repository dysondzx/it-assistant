import logging
import sys


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    return root


logger = setup_logging()