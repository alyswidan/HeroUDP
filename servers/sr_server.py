import os
import uuid

from helpers.logger_utils import get_stdout_logger
from receivers.sr_receiver import SelectiveRepeatReceiver


def start_server(welcoming_port, window_size=15, max_seq_num=-1, loss_prob=0.2):

    CHUNK_SIZE = 500
    logger = get_stdout_logger('sr_server','DEBUG')

    def send_file(init_packet, sr_sender):
        file_name = str(init_packet.data, 'ascii')
        sr_sender.start_data_waiter()

        bytes_in_file = os.stat(file_name).st_size
        number_of_packets = bytes_in_file // CHUNK_SIZE
        number_of_packets += 1 if number_of_packets % CHUNK_SIZE != 0 else 0
        sr_sender.insert_in_buffer(str(uuid.uuid4().hex)[0:6])
        sr_sender.insert_in_buffer(number_of_packets)

        with open(f'../test_files/{file_name}', 'rb') as file:
            for i in range(number_of_packets):
                data_chunk = file.read(CHUNK_SIZE)
                sr_sender.insert_in_buffer(data_chunk)

        sr_sender.insert_in_buffer(bytes(0))
        logger.debug('done putting data into buffer')

        sr_sender.close()



    listening_receiver = SelectiveRepeatReceiver()
    listening_receiver.listen(welcoming_port)

    while True:
        logger.info(f'server listening on port {welcoming_port}')
        client_thread = listening_receiver.accept(send_file, window_size=15, loss_prob=0.2)
