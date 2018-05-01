import logging

from helpers import get_stdout_logger
from lossy_decorator import get_lossy_udt_sender
from receivers.udt_receiver import UDTReceiver
from senders.stop_and_wait_sender import StopAndWaitSender

logger = get_stdout_logger('sw_receiver')
LOSS_PROB = 0.1

class StopAndWaitReceiver:
    def __init__(self):
        self.udt_receiver_class = UDTReceiver
        self.rdt_sender_class = StopAndWaitSender
        self.udt_receiver = self.udt_receiver_class()
        self.udt_listening_receiver = None
        self.states = {'wait_data_0': self.WaitForDataState(self,0),
                       'wait_data_1': self.WaitForDataState(self,1)}
        self.current_state = self.states['wait_data_0']
        self.is_listening = False

    @classmethod
    def from_sw_sender(cls, sw_sender):
        sw_receiver = cls()
        sw_receiver.udt_receiver.socket = sw_sender.udt_receiver.socket
        return sw_receiver

    def listen(self, port):
        """
        This sets up the receiver to start listening for incoming connections on the port passed in as a parameter.
        :param port:
        """
        self.udt_listening_receiver = self.udt_receiver_class()
        self.udt_listening_receiver.bind(port)
        self.is_listening = True

    def receive(self):
        """
        responds to a call from below
        :return packet: type=DataPacket : the received packet
        :return sw_sender: type=StopAndWaitSender : a sender pointed at the source of the packet
        """
        packet, sw_sender = self.current_state.receive()
        self.current_state = self.states['wait_data_0'] if self.is_listening else self.current_state.transition()
        return packet, sw_sender

    def close(self):
        self.udt_receiver.close()
        if self.is_listening:
            self.udt_listening_receiver.close()

    class WaitForDataState:
        def __init__(self, parent, seq_number):
            self.seq_number = seq_number
            self.parent = parent

        def receive(self):
            """
            Waits for a data packet with the corresponding sequence number,
            :return packet: a packet with the corresponding sequence number
            :return sender: a stop and wait sender pointed at the sending side
            """
            receiver =  self.parent.udt_listening_receiver if self.parent.is_listening else self.parent.udt_receiver
            packet, sender_address, udt_sender = None, None, None

            while packet is None or packet.seq_number != self.seq_number:
                if packet is not None:
                    # if we received a retransmission send a duplicate ack
                    udt_sender.send_ack(packet.seq_number)
                    logger.log(logging.INFO, f'received a retransmission and sent a duplicate ack')

                packet, sender_address = receiver.receive()

                udt_sender = get_lossy_udt_sender(LOSS_PROB)(*sender_address,)


            # ack the correct packet
            udt_sender.send_ack(self.seq_number)
            logger.log(logging.INFO, f'received data with sequence number {self.seq_number} ')
            logger.log(logging.INFO, f'sent an ack for {self.seq_number}')
            return packet, self.parent.rdt_sender_class(*sender_address)


        def transition(self):
            return self.parent.states[f'wait_data_{self.seq_number ^ 1}']

