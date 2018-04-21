from threading import Condition, Timer

from packet import DataPacket
from udt_receiver import UDTReceiver
from udt_sender import UDTSender
import logging
from helpers import get_stdout_logger

logger = get_stdout_logger()
TIMEOUT = 0.1
class StopAndWaitSender:

    def __init__(self, server_ip, server_port):

        self.udt_sender = UDTSender(server_ip, server_port)
        self.udt_receiver = UDTReceiver.from_udt_sender(self.udt_sender)
        self.call_from_above_cv = Condition()
        self.current_chunk = None
        self.current_seq_number = 0

        self.timer = None

        self.states = {'wait_data_0':self.WaitForDataState(self, 0),
                       'wait_data_1': self.WaitForDataState(self, 1),
                       'wait_ack_0':  self.WaitForAckState(self, 0),
                       'wait_ack_1':  self.WaitForAckState(self, 1)}

        self.current_state = self.states['wait_data_0']

    def send_data(self, data_chunk):
        """
        when calling this the machine has to be in one of the two waiting for data states
        :param data_chunk: The data chunk to be sent
        :return:
        """
        self.current_state.send(data_chunk)
        self.current_state = self.current_state.transition()
        self.current_state.receive()
        self.current_state = self.current_state.transition()

    class WaitForDataState:
        """
        This class represents any of the two states where the machine waits for a call from the application
        layer to send a chunk of data
        """
        def __init__(self, parent, seq_number):
            self.parent = parent
            self.seq_number = seq_number


        def send(self, data_chunk):
            """
            :param data_chunk: The chunk of data that is to be sent
            :returns the corresponding state function that waits for an ack for this sent packet
            """
            self.parent.udt_sender.send_data(data_chunk, self.seq_number)
            self.parent.current_chunk = data_chunk
            self.parent.current_seq_number = self.seq_number
            self.parent.timer = Timer(TIMEOUT, self.parent.resend_and_set_timer)
            self.parent.timer.start()

        def transition(self):
            return self.parent.states[f'wait_ack_{self.seq_number}']

    class WaitForAckState:
        """
        This class represents any of the two states where the machine is waiting for an ack, the seq_number
        indicates which state exactly
        """
        def __init__(self, parent,seq_number):
            self.parent = parent
            self.seq_number = seq_number

        def receive(self):
            """
            The function busy waits for a packet, when it receives a packet it checks if it's the correct ack,
            if so it cancels the timer and returns the next state, it also notifies any user of the machine who
            is waiting on the call from above condition variable to send data

            :returns Nothing
            """
            packet, sender_address = None, None
            while packet is None or isinstance(packet, DataPacket) or packet.seq_number != self.seq_number:
                packet, sender_address = self.parent.udt_receiver.receive()

            self.parent.timer.cancel()
            logger.log(logging.INFO, f'received an ack for {self.seq_number}')
            # self.parent.call_from_above_cv.notify()

        def transition(self):
            # if we correctly receive the ack for the packet start waiting for data with the opposite sequence number
            return self.parent.states[f'wait_data_{self.seq_number ^ 1}']

        def send(self, data_chunk):
            """
            repeat the action taken by the previous wait for data state
            :param data_chunk:
            :return:
            """
            self.parent.states[f'wait_data_{self.seq_number}'].send(data_chunk)

    def resend_and_set_timer(self):
        """
        this is the callback for the timer, it creates a new timer and calls the send method of the current state
        the current state has to be a waiting for data state
        This function returns nothing since it is meant to be used as a callback
        """
        self.udt_sender.send_data(self.current_chunk, self.current_seq_number)
        self.timer = Timer(TIMEOUT, self.resend_and_set_timer)
        self.timer.start()