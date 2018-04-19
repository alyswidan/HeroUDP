from packet import DataPacket, AckPacket
import logging
from states import *
from socket import *
BUFFER_SIZE = 508


class UDTReceiver:
    def __init__(self, socket):
        self.socket = socket

    def receive(self):
        raw_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)

        if len(raw_packet) == BUFFER_SIZE:
            packet = DataPacket.from_raw(raw_packet)
        else:
            packet = AckPacket.from_raw(raw_packet)

        return packet, server_address


class StopAndWaitReceiver:
    def __init__(self):
        self.udt_receiver = UDTReceiver(socket(AF_INET, SOCK_DGRAM))
        self.is_listening = False
        self.udt_listening_receiver = None
        self.states = {'wait_data_0': WaitingForDataFromBelowSW(0, self),
                       'wait_data_1': WaitingForDataFromBelowSW(1, self)}
        self.current_state = self.states['wait_data_0']

    def listen(self, port):
        self.is_listening = True
        listening_socket = socket(AF_INET, SOCK_DGRAM)
        socket.bind(('', port))
        self.udt_listening_receiver = UDTReceiver(listening_socket)

    def receive(self):
        self.current_state, packet, udt_sender = self.current_state.receive()
        return packet, udt_sender
