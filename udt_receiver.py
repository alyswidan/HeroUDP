
from _socket import AF_INET, SOCK_DGRAM, socket

from packet import DataPacket, AckPacket,CHUNK_SIZE
from helpers import get_stdout_logger
import logging
import os
import select
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
            logger.log(logging.INFO, f'received a data packet from {server_address}')
            packet = DataPacket.from_raw(raw_packet)
        else:
            # logger.log(logging.INFO, 'received an ACk')
            packet = AckPacket.from_raw(raw_packet)

        return packet, server_address


    def bind(self, port):
        self.socket.bind(('', port))

    def close(self):
        self.socket.close()


class InterruptableUDTReceiver:
    def __init__(self, udt_receiver):
        self.udt_receiver = udt_receiver
        udt_receiver.socket.set_blocking(0)
        self.socket = udt_receiver.socket
        self._r_pipe, self._w_pipe = os.pipe()


    def receive(self):
        read, _w, errors = select.select([self._r_pipe, self.socket], [], [self.socket])
        if self.socket in read:
            return self.udt_receiver.receive()
        raise InterruptException

    def interrupt(self):
        os.write(self._w_pipe, "I".encode())


class InterruptException(Exception):
    pass

