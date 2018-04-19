from packet import DataPacket, AckPacket
import logging
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

