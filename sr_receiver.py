from collections import deque
from threading import Semaphore, Lock, current_thread
import time
import logging
from helpers import get_stdout_logger
from sr_sender import SelectiveRepeatSender
from udt_receiver import UDTReceiver
from udt_sender import UDTSender

logger = get_stdout_logger()

class SelectiveRepeatReceiver:

    def __init__(self):
        self.udt_receiver = UDTReceiver()
        self.udt_listening_receiver = UDTReceiver()


    def get_packet(self):
        logger.log(logging.INFO,f'trying to get packet')
        return self.udt_receiver.receive()[0]

    @classmethod
    def from_sender(cls, sr_sender):
        sr_receiver = cls()
        sr_receiver.udt_receiver = UDTReceiver.from_udt_sender(sr_sender.udt_sender)
        return sr_receiver

    def listen(self, port):
        """
        This sets up the receiver to start listening for incoming connections
        on the port passed in as a parameter.
        :param port:
        """
        self.udt_listening_receiver.bind(port)
        self.is_listening = True

    def accept(self):
        if not self.is_listening:
            raise TypeError('non listening receiver cannot accept connections')

        init_packet, client_address = self.udt_listening_receiver.receive()
        return init_packet, client_address