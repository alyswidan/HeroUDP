import time
from collections import deque
from threading import Lock, Condition, Thread

from senders.udt_sender import UDTSender, LossyUDTSender

from helpers.logger_utils import get_stdout_logger
from receivers.udt_receiver import UDTReceiver, InterruptableUDTReceiver
from senders.sr_sender import SelectiveRepeatSender

logger = get_stdout_logger('sr_receiver', 'DEBUG')


class SelectiveRepeatReceiver:

    def __init__(self, window_size=4, max_seq_num=-1, loss_prob=0):
        self.udt_receiver = InterruptableUDTReceiver(UDTReceiver())
        self.udt_listening_receiver = UDTReceiver()
        self.max_seq_num = max(2 * window_size, max_seq_num)
        self.expected_seq_num = 0
        self.data_queue = deque()
        self.data_queue_cv = Condition()
        self.done_receiving = False
        self.waiting_to_close = False
        self.loss_prob = loss_prob
        self.closing_cv = Condition()


    def start_data_waiter(self):
        t = Thread(target=self.wait_for_data)
        t.daemon = True
        t.start()

    def wait_for_data(self):

        while not self.done_receiving:
            packet, sender_address = self.udt_receiver.receive()
            logger.info(f'received {packet.data} from {sender_address}')

            if packet.seq_number == self.expected_seq_num:
                self.send_ack(packet.seq_number, sender_address)
                with self.data_queue_cv:
                    self.data_queue.append(packet)
                    self.data_queue_cv.notify()

    def send_ack(self,seq_number, sender_address):
        udt_sender = LossyUDTSender(UDTSender.from_udt_receiver(self.udt_receiver, *sender_address),
                                                                self.loss_prob)
        udt_sender.send_ack(seq_number)

        logger.info(f'sent an Ack with seq number {seq_number} to {sender_address}')
        self.expected_seq_num = (self.expected_seq_num + 1) % self.max_seq_num

    def get_packet(self):

        with self.data_queue_cv:
            self.data_queue_cv.wait_for(lambda : len(self.data_queue) > 0)
            pkt = self.data_queue.popleft()
            logger.info(f'delivering packet with data {pkt.data} to upper layer')
            return pkt

    @classmethod
    def from_sender(cls, sr_sender, window_size=4, max_seq_num=-1, loss_prob=0):
        sr_receiver = cls(window_size=window_size, max_seq_num=max_seq_num,loss_prob=loss_prob)
        sr_receiver.udt_receiver = InterruptableUDTReceiver(UDTReceiver.from_udt_sender(sr_sender.udt_sender))
        return sr_receiver

    def listen(self, port):
        """
        This sets up the receiver to start listening for incoming connections
        on the port passed in as a parameter.
        :param port:
        """
        self.udt_listening_receiver.bind(port)
        self.is_listening = True

    def accept(self, callback, **sender_args):
        def extended_callback(init_packet, sr_sender):
            time.sleep(1)
            callback(init_packet, sr_sender)

        if not self.is_listening:
            raise TypeError('non listening receiver cannot accept connections')

        init_packet, sender_address = self.udt_listening_receiver.receive()

        logger.info( f'(listener) : received {init_packet.data} from {sender_address}')
        self.send_ack(init_packet.seq_number, sender_address)

        client_thread = Thread(target=extended_callback, args=(init_packet, SelectiveRepeatSender(*sender_address, **sender_args)))
        client_thread.daemon = True
        client_thread.start()

        return client_thread

    def close(self):
        with self.closing_cv:
            while len(self.data_queue) > 0:
                self.closing_cv.wait()

            time.sleep(5) # wait for half a millisecond in case this is just a pause due to delays
            logger.debug('woke up')
            if len(self.data_queue) > 0:
                self.close()

            self.done_receiving = True
            logger.debug('closing client')
