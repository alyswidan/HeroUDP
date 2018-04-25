from collections import deque
from threading import Semaphore, Lock, current_thread
import time
import logging
from helpers import get_stdout_logger
from udt_sender import UDTSender

logger = get_stdout_logger()

class SelectiveRepeatSender:

    def __init__(self, receiver_ip, receiver_port, buffer_size=4, max_seq_num=-1):
        """"
        :param buffer_size : the size of the window
        :param max_seq_num:  maximum sequence number, if -1 or <2*buffer_size it is set to 2*window size
        """
        self.max_seq_num = max(2*buffer_size, max_seq_num)
        self.current_seq_num = -1
        self.buffer = deque()
        self.buffer_lock = Lock()
        self.buffer_full_sem = Semaphore(value=0)
        self.buffer_empty_sem = Semaphore(value=buffer_size-1)
        self.udt_sender = UDTSender(receiver_ip, receiver_port)

    def wait(self):


        while True:
            # time.sleep(3)
            data_chunk = self.get_from_buffer()
            if str(data_chunk, encoding='ascii') == '-1':
                break
            self.udt_sender.send_data(data_chunk,self.get_next_seq_num())
            # packet is not emerging at the client

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
        # TODO: might consider moving this to the udt sender
        if not isinstance(data_chunk, bytes):
            if isinstance(data_chunk, int):
                data_chunk = str(data_chunk)
            if isinstance(data_chunk, str):
               data_chunk = bytes(data_chunk, encoding='ascii')
            else:
                raise ValueError('value of parameter data chunk is not byte like, int or string')

        self.buffer_full_sem.release()
        with self.buffer_lock:
            self.buffer.append(data_chunk)
            logger.log(logging.INFO, f'{current_thread().getName()} inserting {data_chunk}'
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
            data_chunk = self.buffer.popleft()
            logger.log(logging.INFO, f'{current_thread().getName()}  got  {data_chunk}'
                                     f'  buffer size= {len(self.buffer)}')
        self.buffer_empty_sem.release()

        return data_chunk