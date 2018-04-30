import functools
from collections import deque
from collections import namedtuple
from threading import Semaphore, Lock, current_thread, Condition, Timer, Thread
import time
import logging
from helpers import get_stdout_logger
from packet import DataPacket
from udt_receiver import UDTReceiver, InterruptableUDTReceiver
from udt_sender import UDTSender, LossyUDTSender

logger = get_stdout_logger('sr_sender','DEBUG')
TIMEOUT = 0.1

def synchronized(wrapped):
    lock = Lock()
    print(lock, id(lock))
    @functools.wraps(wrapped)
    def _wrap(*args, **kwargs):
        with lock:
            print ("Calling '%s' with Lock %s from thread %s [%s]"
                   % (wrapped.__name__, id(lock),
                   current_thread().name, time.time()))
            result = wrapped(*args, **kwargs)
            print ("Done '%s' with Lock %s from thread %s [%s]"
                   % (wrapped.__name__, id(lock),
                   current_thread().name, time.time()))
            return result
    return _wrap

class SelectiveRepeatSender:


    def __init__(self, receiver_ip, receiver_port, window_size=4, max_seq_num=-1, buffer_size = 5, loss_prob=0):
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
        self.cnt=0

        # the buffer used by the server to pass data chunks and a condition variable to block
        # the thread passing chunks when the buffer is full

        self.buffer = deque()
        self.buffer_cond_var = Condition() # used by the chunk sender to wait for a slot in the queue
        self.window_size = window_size
        self.buffer_size = buffer_size
        self.buffer_consumed = False

        # the window used to buffer packets for retransmission
        self.current_window = deque([self.WindowEntry(None, False) for _ in range(window_size)])
        self.next_slot = 0
        self.base_seq_num = 0

        self.sending_lock = Lock()
        self.packet_timers = {}
        self.acked_pkts_queue = deque() # this is used by a thread waiting for an ack
        self.timed_out_queue = deque()

        self.done_sending = False
        self.waiting_to_close = False
        self.closing_cv = Condition()
        self.udt_sender = LossyUDTSender(UDTSender(receiver_ip, receiver_port), loss_prob)
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
                    self.send_packet(self.get_next_seq_num())

            ack = self.get_ack()

            if ack is not None and self.is_in_window(ack.seq_number):
                logger.debug(f'trying to set {ack.seq_number} as acked {self.current_window} | base={self.base_seq_num}')
                self.current_window[self.get_window_idx(ack.seq_number)].is_acked = True
                self.adjust_window()

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


                try:
                    self.packet_timers[packet.seq_number].cancel()
                except:
                    logger.error(f'timer with for packet {packet.seq_number} not in map')

                self.insert_ack(packet)
                logger.info( f'received an ACk with seq num {packet.seq_number}'
                             f' from {sender_address}')

    def timeout(self, seq_num):
        logger.info(f'{seq_num} timed out, scheduled for retransmition')
        self.retransmit(seq_num)

    def retransmit(self, seq_num):
        if self.is_in_window(seq_num):
            logger.debug(f'retransmitting {seq_num}')
            self.send_packet(seq_num)

    # @synchronized
    def send_packet(self, seq_num):

        logger.debug('entering send_packet')
        data_chunk = self.current_window[self.get_window_idx(seq_num)].data_chunk

        self.udt_sender.send_data(data_chunk, seq_num)
        self.packet_timers[seq_num] = Timer(TIMEOUT, self.timeout, args=(seq_num, ))
        self.packet_timers[seq_num].start()

        logger.info( f'starting the timer for {seq_num}')
        logger.debug('exiting send_packet')

    def add_to_window(self, data_chunk):
        if self.next_slot != self.window_size:
            self.current_window[self.next_slot] = self.WindowEntry(data_chunk, False)
            self.next_slot += 1
            return True
        return False

    def adjust_window(self):
        shifts = 0
        logger.debug( f'window before adjusting = {self.current_window} '
                      f'| base={self.base_seq_num} ({self.cnt})')

        for i, entry in enumerate(self.current_window):
            if not  entry.is_acked:
                break
            shifts += 1
            self.current_window[i] = self.WindowEntry(None, False)


        self.current_window.rotate(-shifts)
        self.base_seq_num = (self.base_seq_num + shifts) % self.max_seq_num


        self.next_slot -= shifts



        logger.debug( f'window after adjusting = {self.current_window} '
                     f'| base={self.base_seq_num} ({self.cnt})')
        self.cnt += 1

        with self.closing_cv:
            if sum([0 if entry.data_chunk is None else 1 for entry in self.current_window])==0:
                self.closing_cv.notify()


    def get_window_idx(self, seq_num):
        seq_num = seq_num if seq_num >= self.base_seq_num else seq_num + self.max_seq_num
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
        self.current_seq_num = self.peek_next_seq_num()
        return self.current_seq_num

    def peek_next_seq_num(self):
        """
        This gets the next sequence number modulo the max sequence number
        :returns the next sequence number:
        """
        return  (self.current_seq_num + 1) % self.max_seq_num

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
        logger.info( '(sr_sender) : closed the sender successfully')



    def get_timed_out_seq_num(self):
        seq_num = None
        try:
            seq_num = self.timed_out_queue.popleft()
        except:
            pass
        return seq_num

    def is_in_window(self, seq_num):
        return seq_num in [i % self.max_seq_num for i in range(self.base_seq_num, self.base_seq_num + self.window_size)]



    class WindowEntry:
        def __init__(self, data_chunk, is_acked):
            self.data_chunk = data_chunk
            self.is_acked = is_acked
        def __str__(self):
            return f'({self.data_chunk}, {self.is_acked})'

        __repr__ = __str__
