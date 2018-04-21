import logging
import sys


def get_stdout_logger(level='INFO'):
    if get_stdout_logger.is_initialized:
        return logging.getLogger()

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
    get_stdout_logger.is_initialized = True

    return stdout_logger
get_stdout_logger.is_initialized = False