from threading import Thread

from sr_receiver import SelectiveRepeatReceiver
from sr_sender import SelectiveRepeatSender

sr_sender = SelectiveRepeatSender('127.0.0.1', 20000)
sr_receiver = SelectiveRepeatReceiver.from_sender(sr_sender)
sr_sender.start_data_waiter()
sr_sender.insert_in_buffer('hi')
sr_receiver.start_data_waiter()
while True:
    print(sr_receiver.get_packet().data)
