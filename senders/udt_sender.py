import base64
import logging
from socket import socket, AF_INET, SOCK_DGRAM

import numpy as np

from helpers.logger_utils import get_stdout_logger
from helpers.packet_utils import compute_checksum
from models.packet import DataPacket, AckPacket

logger = get_stdout_logger('udt_sender','DEBUG')

class UDTSender:
    def __init__(self, server_ip, server_port):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.receiver_address = (server_ip, server_port)

    @classmethod
    def from_udt_receiver(cls, udt_receiver, server_ip, server_port):
        sender = cls(server_ip, server_port)
        sender.socket = udt_receiver.socket
        return sender

    def send_data(self, data_chunk=None, seq_number=None,packet=None):
        logger.debug(f'sent data with seq number {seq_number} to {self.receiver_address}')
        if packet is None:
            packet = DataPacket(data_chunk, seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)

    def send_ack(self, seq_number=None, packet=None):
        logger.debug(f'sent an Ack with seq number {seq_number} to {self.receiver_address}')
        if packet is None:
            packet = AckPacket(seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)

    def close(self):
        logger.log(logging.INFO, 'closing socket')
        self.socket.close()



class LossyUDTSender:
    """
    This is udt sender that losses packets with probability loss_prob
    """
    def __init__(self,udt_sender, loss_prob = 0.1):
        self.udt_sender = udt_sender
        self.loss_prob = loss_prob

    def send_data(self, data_chunk=None, seq_number=None,packet=None):
        if self._get_decision() == 'sent':
            self.udt_sender.send_data(data_chunk, seq_number, packet)
        else:
            logger.info(f'dropping data packet {seq_number}')


    def send_ack(self, seq_number=None,packet=None):
        if self._get_decision() == 'sent':
            self.udt_sender.send_ack(seq_number=seq_number,packet=packet)
        else:
            logger.info(f'dropping ack {seq_number}')


    def _get_decision(self):
        return np.random.choice(['lost', 'sent'], p=[self.loss_prob, 1 - self.loss_prob])


    def __getattribute__(self, attr):
        try:
            found_attr = super(LossyUDTSender, self).__getattribute__(attr)
        except AttributeError:
            pass
        else:
            return found_attr

        found_attr = self.udt_sender.__getattribute__(attr)

        return found_attr

class CorruptingUDTSender:
    """
    This is udt sender that corrupts packets with probability corrupt_prob
    """
    def __init__(self,udt_sender, corrupt_prob = 0):
        self.udt_sender = udt_sender
        self.corrupt_prob = corrupt_prob

    def send_data(self, data_chunk, seq_number):

        packet = DataPacket(data_chunk, seq_number)
        packet.compute_checksum()

        if self._get_decision() == 'leave':
            self.udt_sender.send_data(packet=packet)
        else:
            packet.data = self._corrupt_data(data_chunk)
            self.udt_sender.send_data(packet=packet)
            logger.info(f'corrupting data packet {seq_number}')


    def send_ack(self, seq_number):
        packet = AckPacket(seq_number)
        packet.compute_checksum()
        if self._get_decision() == 'leave':
            self.udt_sender.send_ack(packet=packet)
        else:
            packet.seq_number = seq_number ^ 0xFF
            self.udt_sender.send_ack(packet=packet)
            logger.info(f'corrupting ack {seq_number}')


    def _get_decision(self):
        return np.random.choice(['corrupt', 'leave'], p=[self.corrupt_prob, 1 - self.corrupt_prob])


    def _corrupt_data(self, data):

        bytes_to_corrupt = np.random.choice(range(len(data)),int(len(data)*0.05))
        # choose 5% of the bytes and flip all the bits in the chosen bytes
        return bytes([byte^0xFF if idx in bytes_to_corrupt else byte  for idx,byte in enumerate(data) ])




    def __getattribute__(self, attr):
        try:
            found_attr = super(CorruptingUDTSender, self).__getattribute__(attr)
        except AttributeError:
            pass
        else:
            return found_attr

        found_attr = self.udt_sender.__getattribute__(attr)

        return found_attr
