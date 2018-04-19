from socket import *

from helpers import get_stdout_logger
from packet import *
from threading import Thread
import os
import logging

from receivers import UDTReceiver
from senders import UDTSender

logger = get_stdout_logger()
BUFFER_SIZE = 508
CHUNK_SIZE = 500
WELCOMING_PORT = 20000


def send_file(file_name, client_address):
    file_socket = socket(AF_INET, SOCK_DGRAM)
    udt_sender = UDTSender(file_socket, client_address)

    # get the number of packets required to send the file
    bytes_in_file = os.stat(file_name).st_size
    number_of_packets = bytes_in_file // CHUNK_SIZE
    number_of_packets += 1 if number_of_packets % CHUNK_SIZE != 0 else 0

    udt_sender.send_data(bytes(str(number_of_packets), encoding='ascii'))

    with open(file_name, 'rb') as file:
        for _ in range(number_of_packets):
            data_chunk = file.read(CHUNK_SIZE)
            udt_sender.send_data(data_chunk)


welcoming_socket = socket(AF_INET, SOCK_DGRAM)
welcoming_socket.bind(('', WELCOMING_PORT))
udt_welcoming_receiver = UDTReceiver(welcoming_socket)
logger.log(level=logging.INFO, msg=f'server listening on port {WELCOMING_PORT}')
client_threads = []

while 1:
    init_packet, client_address = udt_welcoming_receiver.receive()
    file_name = init_packet.data
    logger.log(level=logging.INFO, msg=f'client {client_address} requested {file_name}')
    client_threads.append(Thread(target=send_file, args=(file_name, client_address, )))
    client_threads[-1].daemon = True
    client_threads[-1].start()



