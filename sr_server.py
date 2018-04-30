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
    for i in range(1000000):
        logger.debug(f'trying to put {i} ')
        sr_sender.insert_in_buffer(i)

    sr_sender.insert_in_buffer(bytes(0))
    logger.debug( 'done putting data into buffer')

    sr_sender.close()


listening_receiver = SelectiveRepeatReceiver()
listening_receiver.listen(20000)

while True:
    init_packet, client_address = listening_receiver.accept()
    logger.debug(init_packet.data)
    client_thread = Thread(target=send_file, args=('',SelectiveRepeatSender(*client_address,max_seq_num=1000)))
    client_thread.daemon = True
    client_thread.start()
    client_thread.join()
    break


