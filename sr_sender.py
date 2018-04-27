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


    def __init__(self, receiver_ip, receiver_port, window_size=4, max_seq_num=-1, buffer_size = 5):
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
        self.buffer_size = buffer_size

        # the window used to buffer packets for retransmission
        self.current_window = deque([self.WindowEntry(None, False) for _ in range(window_size)])
        self.next_slot = 0
        self.base_seq_num = 0

        self.sending_lock = Lock()
        self.packet_timers = {}
        self.acked_pkts_queue = deque() # this is used by a thread waiting for an ack to tell the main thread about the ack
        self.timed_out_queue = deque()

        self.done_sending = False
        self.waiting_to_close = False
        self.closing_cv = Condition()
        self.udt_sender = UDTSender(receiver_ip, receiver_port)
        self.udt_receiver = UDTReceiver.from_udt_sender(self.udt_sender)


    def start_data_waiter(self):
        sender_thread = Thread(target=self.wait_for_data)
        sender_thread.start()
        return sender_thread


    def wait_for_data(self):
        """
        waits for a packet to be placed in the buffer until it gets a None from the buffer
        :return:
        """
        self.start_ack_waiter() # start listening for any ack
        while not self.done_sending:
            data_chunk = self.get_from_buffer()

            if data_chunk is not None:
                if self.add_to_window(data_chunk):
                    self.send_packet(self.get_next_seq_num())

            ack = self.get_ack()

            if ack is not None:
                self.current_window[self.get_window_idx(ack.seq_number)].is_acked = True
                self.adjust_window()


            timed_out_seq_num = self.get_timed_out_seq_num()
            if timed_out_seq_num is not None:
                self.send_packet(timed_out_seq_num)



    def start_ack_waiter(self):
        ack_waiter = Thread(target=self.wait_for_ack)
        ack_waiter.daemon = True
        ack_waiter.start()

    def wait_for_ack(self):

        while not self.done_sending:
                packet = None
                while packet is None or isinstance(packet, DataPacket):
                    packet, _ = self.udt_receiver.receive()
                    logger.log(logging.INFO, 'in the ack receiving loop')

                self.packet_timers[packet.seq_number].cancel()
                del self.packet_timers[packet.seq_number]

                self.insert_ack(packet)
                logger.log(logging.INFO, f'got an ack for packet {packet.seq_number}')

    def timeout(self, seq_num):
        self.timed_out_queue.append(seq_num)
        logger.log(logging.INFO, f'{seq_num} timed out')

    def send_packet(self, seq_num):


        with self.sending_lock:
            data_chunk = self.current_window[self.get_window_idx(seq_num)].data_chunk
            self.udt_sender.send_data(data_chunk, seq_num)
            self.packet_timers[seq_num] = Timer(TIMEOUT, self.timeout, args=(seq_num, ))
            self.packet_timers[seq_num].start()
            logger.log(logging.INFO, f'sent packet with data {data_chunk}')
            logger.log(logging.INFO, f'starting the wait for {seq_num}')

    def add_to_window(self, data_chunk):
        if self.next_slot != self.window_size:
            logger.log(logging.INFO, f'putting {data_chunk} into slot number {self.next_slot}, base={self.base_seq_num}')
            self.current_window[self.next_slot] = self.WindowEntry(data_chunk, False)
            self.next_slot += 1
            return True
        return False

    def adjust_window(self):
        shifts = 0
        for i, entry in enumerate(self.current_window):
            if not  entry.is_acked:
                break
            shifts += 1
            self.current_window[i] = self.WindowEntry(None, False)


        self.next_slot = self.window_size - shifts
        self.current_window.rotate(-shifts)
        self.base_seq_num += shifts

        logger.log(logging.INFO, f'window after adjusting = {self.current_window}')

        with self.closing_cv:
            self.closing_cv.notify()


    def get_window_idx(self, seq_num):
        return seq_num - self.base_seq_num

    def insert_ack(self, ack):
        self.acked_pkts_queue.append(ack)

    def get_ack(self):
        ack = None
        try:
            ack = self.acked_pkts_queue.popleft()
        except:
            pass

        return ack

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
            self.buffer_cond_var.wait_for(lambda : len(self.buffer) < self.buffer_size)

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
                if self.next_slot != self.window_size:
                    data_chunk = self.buffer.popleft()
                    logger.log(logging.INFO, f'got {data_chunk} from buffer')
            except:
                pass

            self.buffer_cond_var.notify() # tell the producer that a slot is available


        return data_chunk

    def close(self):
        logger.log(logging.INFO, 'attempting to close sender')
        with self.closing_cv:
            self.closing_cv.wait_for(lambda : len(self.packet_timers) == 0)
        self.terminate_waiters()


    def terminate_waiters(self):
        self.udt_receiver.close()
        self.done_sending = True
        self.get_from_buffer() # notify the producer
        logger.log(logging.INFO, 'closed the sender successfully')



    def get_timed_out_seq_num(self):
        seq_num = None
        try:
            seq_num = self.timed_out_queue.popleft()
        except:
            pass
        return seq_num

    class WindowEntry:
        def __init__(self, data_chunk, is_acked):
            self.data_chunk = data_chunk
            self.is_acked = is_acked
        def __str__(self):
            return f'({self.data_chunk}, {self.is_acked})'

        __repr__ = __str__
