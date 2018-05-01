import os
import uuid
from threading import Thread

from helpers import get_stdout_logger
from lossy_decorator import *
from receivers.stop_and_wait_receiver import StopAndWaitReceiver

CHUNK_SIZE = 500
WELCOMING_PORT = 30000
LOSS_PROB = 0.1
logger = get_stdout_logger('sw_server')

def send_file(file_name, sw_sender, client_id):
    # get the number of packets required to send the file
    make_lossy_sender(sw_sender, LOSS_PROB)
    bytes_in_file = os.stat(file_name).st_size
    number_of_packets = bytes_in_file // CHUNK_SIZE
    number_of_packets += 1 if number_of_packets % CHUNK_SIZE != 0 else 0

    sw_sender.send_data(bytes(str(number_of_packets), encoding='ascii'),client_id,-1)

    logger.log(logging.INFO, 'started sending file')

    with open(file_name, 'rb') as file:
        for i in range(number_of_packets):
            data_chunk = file.read(CHUNK_SIZE)
            sw_sender.send_data(data_chunk, client_id, i)

    sw_sender.close()
    logger.log(logging.INFO, '---------------------------------------------------')


welcoming_receiver = make_lossy_receiver(StopAndWaitReceiver(),LOSS_PROB)
welcoming_receiver.listen(WELCOMING_PORT)
logger.log(logging.INFO, f'listening on port {WELCOMING_PORT}')
while 1:
    init_packet, sw_sender  = welcoming_receiver.receive()
    file_name = init_packet.data
    logger.log(level=logging.INFO, msg=f'received a request for file {file_name}')
    client_id = uuid.uuid4().hex[0:6]
    client_thread = Thread(target=send_file, args=(file_name, sw_sender,client_id, ))
    client_thread.daemon = True
    client_thread.start()
