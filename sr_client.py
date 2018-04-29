from threading import Thread

import time

from sr_receiver import SelectiveRepeatReceiver
from sr_sender import SelectiveRepeatSender

sr_sender = SelectiveRepeatSender('127.0.0.1', 20000)
sr_sender.start_data_waiter()
sr_sender.insert_in_buffer('hi')
sr_sender.insert_in_buffer(bytes(0))
sr_sender.close()
sr_receiver = SelectiveRepeatReceiver.from_sender(sr_sender)
sr_receiver.start_data_waiter()
a = []
for _ in range(int(1e6)):
    a.append(sr_receiver.get_packet())
print([item.data for item in  a])
