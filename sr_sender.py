from collections import deque
from threading import Semaphore, Lock, current_thread, Condition
import time
import logging
from helpers import get_stdout_logger
from packet import DataPacket
from udt_receiver import UDTReceiver
from udt_sender import UDTSender

logger = get_stdout_logger()

class SelectiveRepeatSender:

    def __init__(self, receiver_ip, receiver_port, buffer_size=4, max_seq_num=-1):
        """"
        I use deque's because using them as queues is faster than using lists as queues and
        they are thread safe
        :param buffer_size : the size of the window
        :param max_seq_num:  maximum sequence number, if -1 or <2*buffer_size it is set to 2*window size
        """
        self.max_seq_num = max(2*buffer_size, max_seq_num)
        self.current_seq_num = -1

        # the buffer used by the server to pass data chunks and a condition variable to block
        # the thread passing chunks when the buffer is full
        self.buffer = deque()
        self.buffer_cond_var = Condition() # used by the chunk sender to wait for a slot in the queue
        self.buffer_size = buffer_size

        self.udt_sender = UDTSender(receiver_ip, receiver_port)
        self.udt_receiver = UDTReceiver.from_udt_sender(self.udt_sender)

        # the window used to buffer packets for retransmission
        self.current_window = []
        self.base_seq_num = 0 # sequence number of the packet at the base of the window

        self.ack_queue = deque() # this is used by a thread waiting for an ack to tell the main thread about the ack
        self.acked_packets = [False for _ in range(buffer_size)] # used to track which packets in the current window are acked
        self.ack_queue_cond_var = Condition()



    def wait_for_data(self):
        """
        waits for a packet to be placed in the buffer until it gets a None from the buffer
        :return:
        """

        while True:
            # time.sleep(3)
            data_chunk = self.get_from_buffer()

            if data_chunk is not None:
                print(data_chunk)
                self.udt_sender.send_data(data_chunk,self.get_next_seq_num())




    def wait_for_ack(self):

        packet = None
        while packet is None or isinstance(packet, DataPacket):
            packet,_ = self.udt_receiver.receive()

        self.ack_queue.append(packet)


    def insert_ack(self, ack):
        self.ack_queue.append()

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
        if not isinstance(data_chunk, bytes) and data_chunk is not None:
            if isinstance(data_chunk, int):
                data_chunk = str(data_chunk)
            if isinstance(data_chunk, str):
               data_chunk = bytes(data_chunk, encoding='ascii')
            else:
                raise ValueError('value of parameter data chunk is not byte like, int or string')

        with self.buffer_cond_var:
            self.buffer_cond_var.wait_for(lambda : len(self.buffer) < self.buffer_size )
            self.buffer.append(data_chunk)

    def get_from_buffer(self):
        """
        gets a packet from the buffer if there's one, if the buffer is empty it returns None
        :return:
        """
        data_chunk = None
        with self.buffer_cond_var:
            try:
                data_chunk = self.buffer.popleft()
            except:
                pass

            self.buffer_cond_var.notify() # tell the producer that a slot is available


        return data_chunk