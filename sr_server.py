from threading import Thread
from socket import *
from helpers import get_stdout_logger
import logging
import os
import uuid

from sr_sender import SelectiveRepeatSender
from lossy_decorator import *
CHUNK_SIZE = 500
WELCOMING_PORT = 30000
logger = get_stdout_logger()

def send_file(file_name):
    sr_sender = SelectiveRepeatSender()
    sender_thread = Thread(target=sr_sender.wait, name='sender')
    sender_thread.start()
    for i in range(1,9):
        sr_sender.insert_in_buffer(i)

    sr_sender.insert_in_buffer(-1)

    sender_thread.join()


send_file('sa')