
import os
import select
from socket import *

from helpers.logger_utils import get_stdout_logger
from models.packet import DataPacket, AckPacket, CHUNK_SIZE

logger = get_stdout_logger('udt_receiver','DEBUG')
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
            if packet is not None:
                logger.debug( f'received {packet.data} from {server_address}')
        else:
            packet = AckPacket.from_raw(raw_packet)
            if packet is not None:
                logger.debug( f'received an ACk with seq num {packet.seq_number} from {server_address}')

        if packet is None:
            logger.debug('received a corrupted packet')

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
            packet,address = self.udt_receiver.receive()
            if packet is None:
                return self.receive()
            else:
                return packet,address
        raise InterruptException

    def interrupt(self):
        os.write(self._w_pipe, "I".encode())

    def __getattribute__(self, attr):
        try:
            found_attr = super(InterruptableUDTReceiver, self).__getattribute__(attr)
        except AttributeError:
            pass
        else:
            return found_attr

        found_attr = self.udt_receiver.__getattribute__(attr)

        return found_attr


class InterruptException(Exception):
    pass

