from socket import *
from packet import *
from senders import *


class SWState:
    def send_data(self, data_chunk):
        pass

    def receive(self):
        pass


class WaitingForDataFromAboveSW(SWState):
    def __init__(self, seq_number, parent_fsm):
        self.seq_number = seq_number
        self.udt_sender = parent_fsm.udt_sender
        self.timer = parent_fsm.timer
        self.parent_fsm = parent_fsm

    def send_data(self, data_chunk):
        self.udt_sender.send_data(data_chunk)
        self.timer.start()
        self.parent_fsm.call_from_above_cv.notify()
        return self.parent_fsm.states[f'wait_ack_{self.seq_number}']


class WaitingForAckSW(SWState):
    def __init__(self, seq_number, udt_receiver, timer, parent_fsm):
        self.seq_number = seq_number
        self.udt_receiver = udt_receiver
        self.timer = timer
        self.parent_fsm = parent_fsm

    def receive(self):
        packet = None
        while packet is None or isinstance(packet, DataPacket) or packet.seq_number != self.seq_number:
            packet, _ = self.udt_receiver.receive()

        self.timer.stop()
        return self.parent_fsm.states[f'wait_data_{self.seq_number ^ 1}']


class WaitingForDataFromBelowSW(SWState):
    def __init__(self, seq_number, parent_fsm):
        self.seq_number = seq_number
        self.parent_fsm = parent_fsm

    def receive(self):
        packet, sender_address = None, None
        udt_sender = UDTSender(socket(AF_INET, SOCK_DGRAM), sender_address)
        while packet is None or packet.seq_number != self.seq_number:
            if packet is not None:
                udt_sender.send_ack(packet.seq_number)
            packet, sender_address = self.parent_fsm.udt_receiver.receive()

        udt_sender.send_ack(self.seq_number)

        return self.parent_fsm[f'wait_data_{self.seq_number ^ 1}'], packet, udt_sender
