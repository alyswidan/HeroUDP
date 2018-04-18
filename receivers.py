from packet import DataPacket
import logging
BUFFER_SIZE = 508

class UDTReceiver:
    def __init__(self, socket, sender_address):
        self.socket = socket
        self.sender_address = sender_address

    def receive(self):
        raw_init_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)
        init_packet = DataPacket.from_raw(raw_init_packet)
        number_of_packets = int(init_packet.data)
