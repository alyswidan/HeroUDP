from socket import *

from helpers import get_stdout_logger
from packet import *
import logging

from receivers import UDTReceiver
from senders import UDTSender

logger = get_stdout_logger()
BUFFER_SIZE = 508


clientSocket = socket(AF_INET, SOCK_DGRAM)
(file_name, server_ip, server_port) = input('give me the file name, ip and port of the server:\n').split()
udt_receiver = UDTReceiver(clientSocket)

udt_sender = UDTSender(clientSocket, (server_ip, int(server_port)))
udt_sender.send_data(bytes(file_name, encoding='ascii'))

init_packet, server_address = udt_receiver.receive()
number_of_packets = int(init_packet.data)
packets = []
for _ in range(number_of_packets):
    packet, _ = udt_receiver.receive()
    packets.append(packet)
    logger.log(level=logging.INFO, msg=f'received packet with sequence number {packets[-1].seq_number}')
    logger.log(level=logging.DEBUG, msg=f'with data {packets[-1].data}')

with open(f'{file_name}_client', 'wb+') as file:
    for packet in packets:
        file.write(bytes(packet.data, encoding='ascii'))

logger.log(level=logging.INFO, msg='done writing file to disk')

clientSocket.close()
