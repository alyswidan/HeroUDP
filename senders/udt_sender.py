import logging
from socket import socket, AF_INET, SOCK_DGRAM

import numpy as np

from helpers.logger_utils import get_stdout_logger
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

    def send_data(self, data_chunk, seq_number):
        logger.debug(f'sent data with seq number {seq_number} to {self.receiver_address}')
        packet = DataPacket(data_chunk, seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)

    def send_ack(self, seq_number):
        logger.debug(f'sent an Ack with seq number {seq_number} to {self.receiver_address}')
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

    def send_data(self, data_chunk, seq_number):
        if self._get_decision() == 'sent':
            self.udt_sender.send_data(data_chunk, seq_number)
        else:
            logger.info(f'dropping data packet {seq_number}')


    def send_ack(self, seq_number):
        if self._get_decision() == 'sent':
            self.udt_sender.send_ack(seq_number)
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