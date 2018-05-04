from receivers.sr_receiver import SelectiveRepeatReceiver
from senders.sr_sender import SelectiveRepeatSender

def start_client(other_ip, other_port, file_name, window=15, loss_prob=0.2, **kwargs):
    sr_sender = SelectiveRepeatSender(other_ip, other_port)
    sr_sender.start_data_waiter()
    sr_sender.insert_in_buffer(file_name)
    sr_sender.insert_in_buffer(bytes(0))
    sr_sender.close()

    sr_receiver = SelectiveRepeatReceiver.from_sender(sr_sender,window_size=window, loss_prob=loss_prob)
    sr_receiver.start_data_waiter()
    id_pkt = sr_receiver.get_packet() # get an id from the server
    client_id = str(id_pkt.data,'ascii')
    count_pkt = sr_receiver.get_packet() # get the number of packet the server will send
    number_of_packets = int(count_pkt.data)

    with open(f'{file_name}_{client_id}', 'wb+') as file:
        for i in range(number_of_packets):
            file.write(sr_receiver.get_packet().data)
    sr_receiver.close()

