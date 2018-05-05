import logging
from threading import Condition, Timer

from helpers.logger_utils import get_stdout_logger
from models.packet import DataPacket
from receivers.udt_receiver import UDTReceiver, InterruptableUDTReceiver
from senders.udt_sender import UDTSender, LossyUDTSender, CorruptingUDTSender

logger = get_stdout_logger('sw_sender')
TIMEOUT = 0.1
class StopAndWaitSender:

    def __init__(self, server_ip, server_port, loss_prob=0):
        self.server_ip = server_ip
        self.server_port = server_port
        self.udt_sender = CorruptingUDTSender(LossyUDTSender(UDTSender(server_ip, server_port), loss_prob), loss_prob)
        self.udt_receiver = InterruptableUDTReceiver(UDTReceiver.from_udt_sender(self.udt_sender))
        self.call_from_above_cv = Condition()

        self.states = {'wait_data_0':self.WaitForDataState(self, 0),
                       'wait_data_1': self.WaitForDataState(self, 1),
                       'wait_ack_0':  self.WaitForAckState(self, 0),
                       'wait_ack_1':  self.WaitForAckState(self, 1)}

        self.current_state = self.states['wait_data_0']
        self.timers = []

    def send_data(self, data_chunk, client_id, chunk_number):
        """
        when calling this the machine has to be in one of the two waiting for data states
        :param data_chunk: The data chunk to be sent
        :return:
        """
        self.current_state.send(data_chunk, client_id, chunk_number)
        self.current_state = self.current_state.transition()
        self.current_state.receive(client_id, chunk_number)
        self.current_state = self.current_state.transition()


    def resend_data(self, data_chunk, chunk_number, client_id, seq_num):
        """
        this is the callback for the timer, it creates a new timer and calls the send method of the current state
        the current state has to be a waiting for data state
        This function returns nothing since it is meant to be used as a callback
        """
        logger.log(logging.INFO, f'data packet with number {chunk_number} timed out')
        self.states[f'wait_data_{seq_num}'].send(data_chunk, client_id, chunk_number)


    def close(self):
        self.udt_receiver.close()
        self.udt_sender.close()

    class WaitForDataState:
        """
        This class represents any of the two states where the machine waits for a call from the application
        layer to send a chunk of data
        """
        def __init__(self, parent, seq_number):
            self.parent = parent
            self.seq_number = seq_number


        def send(self, data_chunk, client_id, chunk_number):
            """
            :param data_chunk: The chunk of data that is to be sent
            :returns a reference to the timer so that it could be passed to the ack receiver
            """
            self.parent.udt_sender.send_data(data_chunk, self.seq_number)
            logger.log(logging.INFO, f'sent data with number {chunk_number} to {client_id}')
            self.parent.timers.append(Timer(TIMEOUT, self.parent.resend_data,
                          args=(data_chunk, chunk_number, client_id, self.seq_number, )))
            self.parent.timers[-1].start()


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

        def receive(self, client_id, chunk_number):
            """
            The function busy waits for a packet, when it receives a packet it checks if it's the correct ack,
            if so it cancels the timer and returns the next state, it also notifies any user of the machine who
            is waiting on the call from above condition variable to send data

            :returns Nothing
            """
            packet, sender_address = None, None
            while packet is None or isinstance(packet, DataPacket) or\
                                    packet.seq_number != self.seq_number:

                packet, sender_address = self.parent.udt_receiver.receive()


            logger.log(logging.INFO, f'received an ack for {chunk_number} from {client_id}')
            for t in self.parent.timers:
                t.cancel()


        def transition(self):
            # if we correctly receive the ack for the packet start waiting for data with the opposite sequence number
            return self.parent.states[f'wait_data_{self.seq_number ^ 1}']


