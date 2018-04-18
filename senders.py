from packet import DataPacket, AckPacket
import logging


class UDTSender:
    def __init__(self, socket, receiver_address):
        self.socket = socket
        self.receiver_address = receiver_address
        self.current_seq_number = 0

    def send_data(self,data_chunk):
        logging.info(f'sending chunk with sequence number {self.current_seq_number}')
        packet = DataPacket(data_chunk, self.current_seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)
        self.current_seq_number += 1

    def send_ack(self, seq_number):
        logging.info(f'sending ack for packet {seq_number}')
        packet = AckPacket(self.current_seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)