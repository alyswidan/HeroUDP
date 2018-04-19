from socket import *
from packet import DataPacket, AckPacket
from states import *
from threading import Condition, Timer
import logging

from receivers import UDTReceiver
TIMEOUT = 2

class UDTSender:
    def __init__(self, socket, receiver_address):
        self.socket = socket
        self.receiver_address = receiver_address
        self.current_seq_number = 0

    def send_data(self, data_chunk):
        logging.info(f'sending chunk with sequence number {self.current_seq_number}')
        packet = DataPacket(data_chunk, self.current_seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)
        self.current_seq_number += 1

    def send_ack(self, seq_number):
        logging.info(f'sending ack for packet {seq_number}')
        packet = AckPacket(self.current_seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)


class StopAndWaitSender:

    def __init__(self, server_ip, server_port):
        self.udt_sender = UDTSender(socket(AF_INET, SOCK_DGRAM), (server_ip, server_port))
        self.udt_receiver = UDTReceiver(socket(AF_INET, SOCK_DGRAM))
        self.call_from_above_cv = Condition()
        self.current_chunk = None

        def timer_callback(that):
            that.udt_sender.send_data(that.current_chunk)
            that.timer = Timer(TIMEOUT, timer_callback, args=that)
            that.timer.start()

        self.timer = Timer(TIMEOUT, timer_callback, args=self)

        self.states = {'wait_data_0': WaitingForDataFromAboveSW(0, self),
                       'wait_data_1': WaitingForDataFromAboveSW(1, self),
                       'wait_ack_0':  WaitingForAckSW(0, self),
                       'wait_ack_1':  WaitingForAckSW(1, self)}
        self.current_state = self.states['wait_data_0']

    def send_data(self, data_chunk):
        self.current_chunk = data_chunk
        self.current_state = self.current_state.send_data(data_chunk)
        self.current_state.receive()



