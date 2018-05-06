import functools
import time
from collections import deque
from threading import Lock, current_thread, Condition, Timer, Thread

from helpers.logger_utils import get_stdout_logger
from receivers.udt_receiver import UDTReceiver, InterruptableUDTReceiver
from senders.udt_sender import UDTSender, LossyUDTSender, CorruptingUDTSender

logger = get_stdout_logger('gbn_sender','DEBUG')
TIMEOUT = 0.1


class GoBackNSender:


    def __init__(self, receiver_ip, receiver_port, window_size=4, max_seq_num=-1, buffer_size = 5, loss_prob=0):
        """"
        I use deque's because using them as queues is faster than using lists as queues and
        they are thread safe
        :param window_size : the size of the window
        :param max_seq_num:  maximum sequence number, if -1 or <2*window_size it is set to 2*window size
        """
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port

        self.max_seq_num = max(3 * window_size, max_seq_num) + 1
        self.current_seq_num = 1

        # the buffer used by the server to pass data chunks and a condition variable to block
        # the thread passing chunks when the buffer is full

        self.buffer = deque()
        self.buffer_cond_var = Condition() # used by the chunk sender to wait for a slot in the queue
        self.window_size = window_size
        self.buffer_size = buffer_size
        self.buffer_consumed = False

        # the window used to buffer packets for retransmission
        self.current_window = deque([None for _ in range(window_size)])
        self.next_slot = 0
        self.base_seq_num = 1

        self.timer = None
        self.acked_pkts_queue = deque() # this is used by a thread waiting for an ack

        self.done_sending = False
        self.waiting_to_close = False
        self.closing_cv = Condition()
        self.udt_sender = CorruptingUDTSender(LossyUDTSender(UDTSender(receiver_ip, receiver_port), loss_prob), loss_prob)
        self.udt_receiver = InterruptableUDTReceiver(UDTReceiver.from_udt_sender(self.udt_sender))


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
            if data_chunk is not None :
                if self.add_to_window(data_chunk):
                    self.send_packet(self.current_seq_num)
                    self.inc_current_seq_num()

            ack = self.get_ack()

            if ack is not None:
                logger.debug('got an ack from queue')
                if self.is_in_window(ack.seq_number):
                    self.adjust_window(ack.seq_number)


    def start_ack_waiter(self):
        ack_waiter = Thread(target=self.wait_for_ack)
        ack_waiter.daemon = True
        ack_waiter.start()

    def wait_for_ack(self):

        while not self.done_sending:
            try:
                packet, sender_address = self.udt_receiver.receive()
            except:
                continue
            self.insert_ack(packet)
            logger.info( f'received an ACk with seq num {packet.seq_number}'
                         f' from {sender_address}')

    def timeout(self):
        logger.info(f'timer timed out')
        self.start_timer()
        self.retransmit_window()

    def retransmit_window(self):
        logger.debug(f'window before retransmitting = {self.current_window} '
                     f'| base={self.base_seq_num})')

        curr = self.base_seq_num

        for i in range(self.window_size):
            if self.current_window[i] is None:
                break

            logger.info(f'retransmitting packet {curr}')
            self.send_packet(curr)
            curr = self.get_next_num(curr , 1)

    def send_packet(self, seq_num):

        """This expects the packet with sequence number (seq_num) to be in the window"""


        try:
            logger.debug('entering send_packet')
            w = self.get_window_idx(seq_num)
            logger.debug(f'window index is {w}')
            data_chunk = self.current_window[w]
            logger.debug(f'sending {data_chunk} at {self.get_window_idx(seq_num)}')
            self.udt_sender.send_data(data_chunk, seq_num)
        except:
            logger.error(f'{self.current_window} | {self.base_seq_num}')
        if self.base_seq_num == self.current_seq_num:
            self.start_timer()
            logger.info( f'starting the timer for {seq_num}')


        logger.debug('exiting send_packet')

    def add_to_window(self, data_chunk):
        if self.next_slot != self.window_size:
            self.current_window[self.next_slot] = data_chunk
            self.next_slot += 1
            return True
        return False


    def adjust_window(self, seq_num):
        """
        :param seq_num: sequence number of the ack received
        :return:
        """

        logger.debug(f'window before adjusting = {self.current_window} '
                     f'| base={self.base_seq_num})')


        window_idx = self.get_window_idx(seq_num)
        logger.debug(f'window index = {window_idx}')
        shifts = window_idx + 1

        for i in range(window_idx, -1, -1):
            self.current_window[i] = None


        self.current_window.rotate(-shifts)
        self.base_seq_num = self.get_next_num(seq_num, 1)
        self.next_slot -= shifts

        logger.debug(f'window after adjusting = {self.current_window} '
                     f'| base={self.base_seq_num})')

        if self.base_seq_num == self.current_seq_num:
            self.stop_timer()
        else:
            self.start_timer()

        with self.closing_cv:
            logger.debug(f'base={self.base_seq_num}, curr seq num={self.current_seq_num}')
            if self.base_seq_num == self.current_seq_num: # if the window is empty
                self.closing_cv.notify()

    def start_timer(self):
        self.stop_timer()
        self.timer = Timer(TIMEOUT, self.timeout)
        self.timer.start()

    def stop_timer(self):
        if self.timer is not None:
            self.timer.cancel()


    def get_window_idx(self, seq_num):

        if seq_num == self.base_seq_num-1 or (seq_num == self.max_seq_num - 1 and self.base_seq_num == 1):
            return -1

        seq_num = seq_num if seq_num >= self.base_seq_num else seq_num + self.max_seq_num-1
        logger.debug(f'getting window index for {seq_num} as {seq_num - self.base_seq_num} '
                     f'| {self.current_window} | base={self.base_seq_num}')
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


    def get_next_num(self, num, delta):
        """
        returns the next number in the sequence modulo the max sequence number
        given we start counting at 1 not 0
        :param num: the number to increment
        :param delta: by how much we want to increment this number
        :return:
        """

        next_num = (num + delta) % self.max_seq_num
        return next_num + 1 if next_num == 0 else next_num



    def inc_current_seq_num(self):
        """
        This gets the next sequence number modulo the max sequence number
        :returns the next sequence number:
        """
        logger.debug(f'incrementing curr sn from {self.current_seq_num} to {self.get_next_num(self.current_seq_num, 1)}')
        self.current_seq_num = self.get_next_num(self.current_seq_num, 1)
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
            logger.debug( f'putting {data_chunk} in buffer')

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
                    logger.debug( f'got {data_chunk} from buffer')
                    if len(data_chunk) == 0:
                        self.buffer_consumed = True
                        data_chunk = None
            except:
                pass

            self.buffer_cond_var.notify() # tell the producer that a slot is available

        return data_chunk

    def close(self):
        logger.debug( 'attempting to close sender')
        with self.closing_cv:
            self.closing_cv.wait_for(lambda : self.buffer_consumed)
            self.terminate_waiters()

    def terminate_waiters(self):
        # self.udt_receiver.close()
        self.done_sending = True
        self.get_from_buffer() # notify the producer
        self.udt_receiver.interrupt()
        logger.info( 'closed the sender successfully')

    def is_in_window(self, seq_num):
        is_in = False
        curr = self.base_seq_num
        for i in range(self.window_size):
            if curr == seq_num:
                return True
            curr = self.get_next_num(curr, 1)
        return False