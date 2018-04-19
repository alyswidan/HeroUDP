import logging
import sys


def get_stdout_logger(level='INFO'):
    logging_level = getattr(logging, level.upper(), None)
    if not isinstance(logging_level, int):
        raise ValueError(f'invalid log level {level}')
    stdout_logger = logging.getLogger()
    stdout_logger.setLevel(logging_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    stdout_logger.addHandler(handler)
    return stdout_logger