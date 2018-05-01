from threading import Thread
from socket import *
from helpers import get_stdout_logger
import logging
import os
import uuid
import time
from sr_receiver import SelectiveRepeatReceiver
from sr_sender import SelectiveRepeatSender
from lossy_decorator import *
CHUNK_SIZE = 500
WELCOMING_PORT = 30000
logger = get_stdout_logger('sr_server','DEBUG')

def send_file(file_name, sr_sender):
    time.sleep(1) # this is a hack
    sr_sender.start_data_waiter()

    bytes_in_file = os.stat(file_name).st_size
    number_of_packets = bytes_in_file // CHUNK_SIZE
    number_of_packets += 1 if number_of_packets % CHUNK_SIZE != 0 else 0
    sr_sender.insert_in_buffer(str(uuid.uuid4().hex)[0:6])
    sr_sender.insert_in_buffer(number_of_packets)

    with open(file_name, 'rb') as file:
        for i in range(number_of_packets):
            data_chunk = file.read(CHUNK_SIZE)
            sr_sender.insert_in_buffer(data_chunk)

    sr_sender.insert_in_buffer(bytes(0))
    logger.debug('done putting data into buffer')

    sr_sender.close()



listening_receiver = SelectiveRepeatReceiver()
listening_receiver.listen(20000)

while True:
    init_packet, client_address = listening_receiver.accept()
    logger.debug(init_packet.data)
    client_thread = Thread(target=send_file, args=('text_test',SelectiveRepeatSender(*client_address,window_size=15,loss_prob=0.2)))
    client_thread.daemon = True
    client_thread.start()


