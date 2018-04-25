from threading import Thread

from sr_receiver import SelectiveRepeatReceiver
from sr_sender import SelectiveRepeatSender

sr_sender = SelectiveRepeatSender('127.0.0.1', 20000)
sr_receiver = SelectiveRepeatReceiver.from_sender(sr_sender)
sender_thread = Thread(target=sr_sender.wait_for_data, name='sender')
sender_thread.start()
sr_sender.insert_in_buffer('hi')

while True:
    print(sr_receiver.get_packet().data)
