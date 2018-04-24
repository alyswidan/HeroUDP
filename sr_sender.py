from collections import deque
from threading import Semaphore, Lock, current_thread
import time
import logging
from helpers import get_stdout_logger
from packet import DataPacket

logger = get_stdout_logger()

class SelectiveRepeatSender:

    def __init__(self, buffer_size=4, max_seq_num=-1):
        """

        :param buffer_size : the size of the window
        :param max_seq_num:  maximum sequence number, if -1 or <2*buffer_size it is set to 2*window size
        """


        self.max_seq_num = max(2*buffer_size, max_seq_num)
        self.current_seq_num = -1
        self.buffer = deque()
        self.buffer_lock = Lock()
        self.buffer_full_sem = Semaphore(value=0)
        self.buffer_empty_sem = Semaphore(value=buffer_size-1)


    def wait(self):


        while True:
            time.sleep(3)
            packet = self.get_from_buffer()
            if str(packet.data, encoding='ascii') == '-1':
                break

    def get_next_seq_num(self):
        """
        This gets the next sequence number modulo the max sequence number
        :returns the next sequence number:
        """
        self.current_seq_num += 1
        self.current_seq_num %= self.max_seq_num
        return self.current_seq_num

    def insert_in_buffer(self, data_chunk):
        """
        inserts the data chunk into the buffer if there's an empty slot
        :param data_chunk: any of the types(int, string, byte-like)
        :raises Value error if data_chunk is any other type
        """

        if not isinstance(data_chunk, bytes):
            if isinstance(data_chunk, int):
                data_chunk = str(data_chunk)
            if isinstance(data_chunk, str):
               data_chunk = bytes(data_chunk, encoding='ascii')
            else:
                raise ValueError('value of parameter data chunk is not byte like, int or string')

        self.buffer_full_sem.release()
        with self.buffer_lock:
            packet = DataPacket(data_chunk, self.get_next_seq_num())
            self.buffer.append(packet)
            logger.log(logging.INFO, f'{current_thread().getName()} inserting {packet}'
                                     f' buffer size= {len(self.buffer)}')

        self.buffer_empty_sem.acquire()


    def get_from_buffer(self):
        """
        gets a packet from the buffer if there's one, if the buffer is empty it blocks the
        thread until an element becomes available
        :return:
        """
        self.buffer_full_sem.acquire()
        with self.buffer_lock:
            packet = self.buffer.popleft()
            logger.log(logging.INFO, f'{current_thread().getName()}  got  {packet}'
                                     f'  buffer size= {len(self.buffer)}')
        self.buffer_empty_sem.release()

        return packet

