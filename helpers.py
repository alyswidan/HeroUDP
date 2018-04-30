import logging
import sys


def get_stdout_logger(name='root',level='INFO'):
    # if get_stdout_logger.is_initialized:
    #     return logging.getLogger()

    logging_level = getattr(logging, level.upper(), None)
    if not isinstance(logging_level, int):
        raise ValueError(f'invalid log level {level}')

    stdout_logger = logging.getLogger(name)
    stdout_logger.setLevel(logging_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    stdout_logger.addHandler(handler)
    get_stdout_logger.is_initialized = True

    return stdout_logger
get_stdout_logger.is_initialized = False


# def delegate_calls(delegate_to):
#     def wrapper(cls):
#         def _get_attr(self, attr):
#             try:
#                 found_attr = super(cls, self).__getattribute__(attr)
#             except AttributeError:
#                 pass
#             else:
#                 return found_attr
#
#             found_attr = .__getattribute__(attr)
#
#             return found_attr
#         setattr(cls, '__getattribute__', _get_attr)
#         return cls
#     return wrapper
