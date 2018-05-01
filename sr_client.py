from threading import Thread

import time

from sr_receiver import SelectiveRepeatReceiver
from sr_sender import SelectiveRepeatSender

sr_sender = SelectiveRepeatSender('127.0.0.1', 20000)
sr_sender.start_data_waiter()
sr_sender.insert_in_buffer('text_test')
sr_sender.insert_in_buffer(bytes(0))
sr_sender.close()
sr_receiver = SelectiveRepeatReceiver.from_sender(sr_sender,window_size=15, loss_prob=0.2)
sr_receiver.start_data_waiter()
first_pkt = sr_receiver.get_packet()
number_of_packets = int(first_pkt.data)

with open(f'text_test_client', 'wb+') as file:
    for i in range(number_of_packets):
        file.write(sr_receiver.get_packet().data)


sr_receiver.close()
