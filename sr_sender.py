from collections import deque
from collections import namedtuple
from threading import Semaphore, Lock, current_thread, Condition, Timer, Thread
import time
import logging
from helpers import get_stdout_logger
from packet import DataPacket
from udt_receiver import UDTReceiver, InterruptableUDTReceiver
from udt_sender import UDTSender

logger = get_stdout_logger()
TIMEOUT = 0.1

class SelectiveRepeatSender:

    def __init__(self, receiver_ip, receiver_port, window_size=4, max_seq_num=-1):
        """"
        I use deque's because using them as queues is faster than using lists as queues and
        they are thread safe
        :param window_size : the size of the window
        :param max_seq_num:  maximum sequence number, if -1 or <2*window_size it is set to 2*window size
        """
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port

        self.max_seq_num = max(2 * window_size, max_seq_num)
        self.current_seq_num = -1

        # the buffer used by the server to pass data chunks and a condition variable to block
        # the thread passing chunks when the buffer is full
        self.buffer = deque()
        self.buffer_cond_var = Condition() # used by the chunk sender to wait for a slot in the queue
        self.window_size = window_size

        # the window used to buffer packets for retransmission
        self.WindowEntry = namedtuple('WindowEntry', ['data_chunk', 'is_acked'])
        self.current_window = deque([self.WindowEntry(None, False) for _ in range(window_size)])
        self.next_slot = 0
        self.base_seq_num = 0

        self.required_acks_queue = deque() # used by the data waiter
                                           #  thread to tell the ack
                                           #  waiter it requires an ack for this packet
        self.acked_pkts_queue = deque() # this is used by a thread waiting for an ack to tell the main thread about the ack
        self.timed_out_queue = deque()

        self.done_sending = False
        self.waiting_to_close = False
        self.udt_sender = UDTSender(receiver_ip, receiver_port)


    def start_data_waiter(self):
        sender_thread = Thread(target=self.wait_for_data)
        sender_thread.start()


    def wait_for_data(self):
        """
        waits for a packet to be placed in the buffer until it gets a None from the buffer
        :return:
        """
        while not self.done_sending:
            data_chunk = self.get_from_buffer()
            if data_chunk is not None:
                self.add_to_window(data_chunk)
                self.start_ack_waiter()

            ack = self.get_ack()

            if ack is not None:
                self.current_window[self.get_window_idx(ack.seq_num)].is_acked = True
                self.adjust_window()

    def start_ack_waiter(self):
        seq_num = self.get_next_seq_num()
        udt_sender = self.send_packet(seq_num)
        self.udt_sender = udt_sender
        ack_waiter = Thread(target=self.wait_for_ack, args=(seq_num, udt_sender,))
        ack_waiter.daemon = True
        ack_waiter.start()

    def add_to_window(self, data_chunk):
        self.current_window[self.next_slot] = self.WindowEntry(data_chunk, False)
        self.next_slot += 1

    def adjust_window(self):
        shifts = 0
        for i, _, is_acked in enumerate(self.current_window):
            if not is_acked:
                break
            shifts += 1
            self.current_window[i] = self.WindowEntry(None, False)

        self.next_slot -= shifts
        self.current_window.rotate(-shifts)

        if self.waiting_to_close and len(self.current_window) == 0:
            self.done_sending = True

    def send_packet(self, seq_num):
        udt_sender = UDTSender(self.receiver_ip, self.receiver_port)
        data_chunk = self.current_window[self.get_window_idx(seq_num)].data_chunk
        udt_sender.send_data(data_chunk, seq_num)
        logger.log(logging.INFO, f'sent packet with data {data_chunk}')
        return udt_sender

    def wait_for_ack(self, seq_num, udt_sender):
        udt_receiver = InterruptableUDTReceiver(UDTReceiver.from_udt_sender(udt_sender))
        packet_timer = Timer(TIMEOUT, udt_receiver.interrupt)
        packet_timer.start()

        packet = None
        while packet is None or isinstance(packet, DataPacket):
            try:
                packet, _ = udt_receiver.receive()
            except: # the timer fired
                logger.log(logging.INFO, f'packet with {seq_num} timed out')
                self.send_packet(seq_num)
                packet_timer = Timer(TIMEOUT, udt_receiver.interrupt)

        packet_timer.cancel()
        self.insert_ack(packet)
        logger.log(logging.INFO, f'got an ack for packet {seq_num}')
        udt_sender.close()




    def get_window_idx(self, seq_num):
        return seq_num - self.base_seq_num

    def insert_ack(self, ack):
        self.acked_pkts_queue.append()

    def get_ack(self):
        ack = None
        try:
            ack = self.acked_pkts_queue.popleft()
        except:
            pass

        return ack

    def slot_available_in_window(self):
        return self.next_slot != self.window_size

    def get_next_seq_num(self):
        """
        This gets the next sequence number modulo the max sequence number
        :returns the next sequence number:
        """
        self.current_seq_num = (self.current_seq_num + 1) % self.max_seq_num
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
            self.buffer_cond_var.wait_for(self.slot_available_in_window)
            self.buffer.append(data_chunk)
            logger.log(logging.INFO, f'put {data_chunk} in buffer')

    def get_from_buffer(self):
        """
        gets a packet from the buffer if there's one, if the buffer is empty it returns None
        :return:
        """
        data_chunk = None
        with self.buffer_cond_var:
            try:
                data_chunk = self.buffer.popleft()
                logger.log(logging.INFO, f'got {data_chunk} from buffer')
            except:
                pass

            self.buffer_cond_var.notify() # tell the producer that a slot is available


        return data_chunk

    def close(self):
        if len(self.current_window) == 0:
            self.done_sending = True
        else:
            self.waiting_to_close = True
