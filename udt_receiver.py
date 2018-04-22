from _socket import AF_INET, SOCK_DGRAM, socket

from packet import DataPacket, AckPacket,CHUNK_SIZE
from helpers import get_stdout_logger
import logging
logger = get_stdout_logger()
BUFFER_SIZE = CHUNK_SIZE + 8

class UDTReceiver:
    def __init__(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)

    @classmethod
    def from_udt_sender(cls, udt_sender ):
        receiver = cls()
        receiver.socket = udt_sender.socket
        return receiver

    def receive(self):
        raw_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)


        if len(raw_packet) == BUFFER_SIZE:
            # logger.log(logging.INFO, 'received a data packet')
            packet = DataPacket.from_raw(raw_packet)
        else:
            # logger.log(logging.INFO, 'received an ACk')
            packet = AckPacket.from_raw(raw_packet)

        return packet, server_address

    def bind(self, port):
        self.socket.bind(('', port))

    def close(self):
        self.socket.close()