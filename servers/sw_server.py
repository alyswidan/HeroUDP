import os
import uuid
from threading import Thread
import logging
from helpers.logger_utils import get_stdout_logger
from receivers.stop_and_wait_receiver import StopAndWaitReceiver

CHUNK_SIZE = 500
logger = get_stdout_logger('sw_server')

def start_server(welcoming_port, loss_prob):
    def send_file(file_name, sw_sender, client_id):
        # get the number of packets required to send the fil
        bytes_in_file = os.stat(file_name).st_size
        number_of_packets = bytes_in_file // CHUNK_SIZE
        number_of_packets += 1 if number_of_packets % CHUNK_SIZE != 0 else 0

        sw_sender.send_data(bytes(client_id, encoding='ascii'), client_id, -1)
        sw_sender.send_data(bytes(str(number_of_packets), encoding='ascii'),client_id,-1)


        logger.info(f'started sending {file_name} to {(sw_sender.server_ip, sw_sender.server_port)}')

        with open(f'../test_files/{file_name}', 'rb') as file:
            for i in range(number_of_packets):
                data_chunk = file.read(CHUNK_SIZE)
                sw_sender.send_data(data_chunk, client_id, i)
        sw_sender.close()

        logger.info(f'done sending {file_name} to {(sw_sender.server_ip, sw_sender.server_port)}')


    welcoming_receiver = StopAndWaitReceiver(loss_prob)
    welcoming_receiver.listen(welcoming_port)
    logger.info( f'listening on port {welcoming_port}')
    while 1:
        init_packet, sw_sender  = welcoming_receiver.receive()
        file_name = init_packet.data
        logger.info(f'received a request for file {file_name}')
        client_id = uuid.uuid4().hex[0:6]
        client_thread = Thread(target=send_file, args=(file_name, sw_sender,client_id, ))
        client_thread.daemon = True
        client_thread.start()

start_server(20000,0.2)