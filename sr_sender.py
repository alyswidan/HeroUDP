from collections import deque
from threading import Semaphore, Lock, current_thread
import time
import logging
from helpers import get_stdout_logger
logger = get_stdout_logger()

class SelectiveRepeatSender:

    def __init__(self, buffer_size=4):
        self.buffer = deque()
        self.buffer_lock = Lock()
        self.buffer_full_sem = Semaphore(value=0)
        self.buffer_empty_sem = Semaphore(value=buffer_size-1)


    def wait(self):


        while True:
            time.sleep(3)
            elem = self.get_from_buffer()
            if elem < 0:
                break


    def insert_in_buffer(self, data_chunk):
        self.buffer_full_sem.release()
        with self.buffer_lock:
            self.buffer.append(data_chunk)
            logger.log(logging.INFO, f'{current_thread().getName()} inserting {data_chunk} buffer size= {len(self.buffer)}')

        self.buffer_empty_sem.acquire()


    def get_from_buffer(self):
        self.buffer_full_sem.acquire()
        with self.buffer_lock:
            elem = self.buffer.popleft()
            logger.log(logging.INFO, f'{current_thread().getName()}  got  {elem}  buffer size= {len(self.buffer)}')
        self.buffer_empty_sem.release()

        return elem

