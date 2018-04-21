from socket import socket,AF_INET, SOCK_DGRAM
from packet import DataPacket, AckPacket
import logging
from helpers import get_stdout_logger

logger = get_stdout_logger()

class UDTSender:
    def __init__(self, server_ip, server_port):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.receiver_address = (server_ip, server_port)

    def send_data(self, data_chunk, seq_number):
        # logger.log(logging.INFO, 'sent a data packet')
        packet = DataPacket(data_chunk, seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)

    def send_ack(self, seq_number):
        # logger.log(logging.INFO, 'sent an Ack')
        packet = AckPacket(seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)