from socket import *
from threading import Timer

from packet import DataPacket, AckPacket
import logging

from receivers import UDTReceiver

TIMEOUT = 2
WINDOW_SIZE = 5


class UDTSender:
    def __init__(self, socket, receiver_address):
        self.socket = socket
        self.receiver_address = receiver_address
        self.current_seq_number = 0

    def send_data(self, data_chunk):
        logging.info(f'sending chunk with sequence number {self.current_seq_number}')
        packet = DataPacket(data_chunk, self.current_seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)
        """
        i removed the increment from here not to have side effects else where
        """

    def send_ack(self, seq_number):
        logging.info(f'sending ack for packet {seq_number}')
        packet = AckPacket(self.current_seq_number)
        self.socket.sendto(packet.get_raw(), self.receiver_address)


class GoBackNSender:
    def __init__(self, server_ip, server_port):
        self.udt_sender = UDTSender(socket(AF_INET, SOCK_DGRAM), (server_ip, server_port))
        self.udt_receiver = UDTReceiver(socket(AF_INET, SOCK_DGRAM))
        self.base = 1
        self.nextSeqNum = 1
        self.window_size = WINDOW_SIZE
        self.send_packets = []

        def timer_callback(that):
            """
            this function will happen when timeout occur and will resend the queued packets
            :param that:
            :return:
            """
            that.timer = Timer(TIMEOUT, timer_callback, args=that)
            that.timer.start()
            # loop over the queue and send again
            for idx in range(self.base, self.nextSeqNum-1):
                self.udt_sender.send_data(self.send_packets[idx].get_raw())

        self.timer = Timer(TIMEOUT, timer_callback, args=self)

    def send_data(self, data_chunk):
        if self.nextSeqNum < self.base + self.window_size:
            self.send_packets[self.nextSeqNum] = DataPacket(data_chunk, self.nextSeqNum)
            # nextSeqNum is incremented after sending that is why I removed it from send_Data func
            self.udt_sender.send_data(self.send_packets[self.nextSeqNum].get_raw())
            if self.base == self.nextSeqNum:
                self.timer.start()
            self.nextSeqNum += 1
        else:
            pass  # refuse the data as window is full
