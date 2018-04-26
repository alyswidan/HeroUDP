from collections import deque
from threading import Semaphore, Lock, current_thread, Condition, Thread
import time
import logging
from helpers import get_stdout_logger
from sr_sender import SelectiveRepeatSender
from udt_receiver import UDTReceiver
from udt_sender import UDTSender

logger = get_stdout_logger()

class SelectiveRepeatReceiver:

    def __init__(self, window_size=4):
        self.udt_receiver = UDTReceiver()
        self.udt_listening_receiver = UDTReceiver()
        self.current_window = deque([None for _ in range(window_size)])
        self.window_size = window_size
        self.base_seq_num = 0
        self.data_queue = deque()
        self.data_queue_cv = Condition()
        self.done_receiving = False
        self.waiting_to_close = False


    def start_data_waiter(self):
        t = Thread(target=self.wait_for_data)
        t.daemon = True
        t.start()


    def wait_for_data(self):

        while not self.done_receiving:
            logger.log(logging.INFO, 'in the waiter loop')
            packet, sender_address = None, None
            while packet is None:
                packet, sender_address = self.udt_receiver.receive()

            logger.log(logging.INFO, f'got {packet.data} from {sender_address}')
            udt_sender = UDTSender(*sender_address)
            udt_sender.send_ack(packet.seq_number)
            self.adjust_window(packet)

    def adjust_window(self, packet):
        if packet.seq_number in range(self.base_seq_num, self.base_seq_num + self.window_size):
            self.current_window[packet.seq_number - self.base_seq_num] = packet

        shifts = 0
        for i, pkt in enumerate(self.current_window):
            if pkt is None:
                break

            logger.log(logging.INFO, f'delivering packet with data {pkt.data} to upper layer')
            self.data_queue.append(pkt)
            with self.data_queue_cv:
                self.data_queue_cv.notify()
            self.current_window[i] = None
            shifts += 1

        self.current_window.rotate(-shifts)
        self.base_seq_num += shifts


    def get_packet(self):

        with self.data_queue_cv:
            self.data_queue_cv.wait_for(lambda : len(self.data_queue) > 0)
            return self.data_queue.popleft()

    @classmethod
    def from_sender(cls, sr_sender):
        sr_receiver = cls()
        sr_receiver.udt_receiver = UDTReceiver.from_udt_sender(sr_sender.udt_sender)
        return sr_receiver

    def listen(self, port):
        """
        This sets up the receiver to start listening for incoming connections
        on the port passed in as a parameter.
        :param port:
        """
        self.udt_listening_receiver.bind(port)
        self.is_listening = True

    def accept(self):
        if not self.is_listening:
            raise TypeError('non listening receiver cannot accept connections')

        init_packet, sender_address = self.udt_listening_receiver.receive()
        logger.log(logging.INFO, f'got {init_packet.data} from {sender_address}')
        udt_sender = UDTSender(*sender_address)
        udt_sender.send_ack(init_packet.seq_number)
        self.adjust_window(init_packet)
        return init_packet, sender_address

    def close(self):
        if len(self.data_queue) == 0:
            self.done_receiving = True
        else:
            self.waiting_to_close = True
