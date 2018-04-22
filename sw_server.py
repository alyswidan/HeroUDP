from threading import Thread
from socket import *
from helpers import get_stdout_logger
import logging
import os

from stop_and_wait_receiver import StopAndWaitReceiver

CHUNK_SIZE = 500
WELCOMING_PORT = 30000
logger = get_stdout_logger()

def send_file(file_name, sw_sender):
    # get the number of packets required to send the file
    bytes_in_file = os.stat(file_name).st_size
    number_of_packets = bytes_in_file // CHUNK_SIZE
    number_of_packets += 1 if number_of_packets % CHUNK_SIZE != 0 else 0

    sw_sender.send_data(bytes(str(number_of_packets), encoding='ascii'))

    logger.log(logging.INFO, 'started sending file')

    with open(file_name, 'rb') as file:
        for _ in range(number_of_packets):
            data_chunk = file.read(CHUNK_SIZE)
            sw_sender.send_data(data_chunk)

    sw_sender.close()
    logger.log(logging.INFO, '---------------------------------------------------')


welcoming_receiver = StopAndWaitReceiver()
welcoming_receiver.listen(WELCOMING_PORT)
logger.log(logging.INFO, f'listening on port {WELCOMING_PORT}')
while 1:
    init_packet, sw_sender  = welcoming_receiver.receive()
    file_name = init_packet.data
    logger.log(level=logging.INFO, msg=f'received a request for file {file_name}')
    client_thread = Thread(target=send_file, args=(file_name, sw_sender,))
    client_thread.daemon = True
    client_thread.start()
