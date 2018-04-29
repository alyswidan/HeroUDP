
from socket import *
from threading import current_thread
from packet import DataPacket, AckPacket,CHUNK_SIZE
from helpers import get_stdout_logger
import logging
import os
import select
logger = get_stdout_logger()
QUEUE_SIZE = 50
BUFFER_SIZE = (CHUNK_SIZE + 8)*QUEUE_SIZE

class UDTReceiver:
    def __init__(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.socket.setsockopt(SOL_SOCKET, SO_RCVBUF, BUFFER_SIZE)

    @classmethod
    def from_udt_sender(cls, udt_sender ):
        receiver = cls()
        receiver.socket = udt_sender.socket
        return receiver

    def receive(self):
        raw_packet, server_address = self.socket.recvfrom(BUFFER_SIZE)

        if len(raw_packet) == BUFFER_SIZE//QUEUE_SIZE:

            packet = DataPacket.from_raw(raw_packet)
            logger.log(logging.INFO, f'(udt_receiver) ({current_thread()}) : received {packet.data} from {server_address}')
        else:
            packet = AckPacket.from_raw(raw_packet)
            logger.log(logging.INFO, f'(udt_receiver) ({current_thread()}) : received an ACk with seq num {packet.seq_number} from {server_address}')

        return packet, server_address


    def bind(self, port):
        self.socket.bind(('', port))

    def close(self):
        self.socket.close()


class InterruptableUDTReceiver:
    def __init__(self, udt_receiver):
        self.udt_receiver = udt_receiver
        udt_receiver.socket.setblocking(0)
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

