from receivers.gbn_receiver import GoBackNReceiver
from senders.gbn_sender import GoBackNSender

def start_client(other_ip, other_port, file_name, loss_prob=0.2, **kwargs):
    gbn_sender = GoBackNSender(other_ip, other_port)
    gbn_sender.start_data_waiter()
    gbn_sender.insert_in_buffer(file_name)
    gbn_sender.insert_in_buffer(bytes(0))
    gbn_sender.close()

    gbn_receiver = GoBackNReceiver.from_sender(gbn_sender,max_seq_num=100000, loss_prob=loss_prob)
    gbn_receiver.start_data_waiter()
    id_pkt = gbn_receiver.get_packet() # get an id from the server
    client_id = str(id_pkt.data,'ascii')
    count_pkt = gbn_receiver.get_packet() # get the number of packet the server will send
    number_of_packets = int(count_pkt.data)

    with open(f'HeroUDP/client_output/files/{file_name}_{client_id}_gbn', 'wb+') as file:
        for i in range(number_of_packets):
            file.write(gbn_receiver.get_packet().data)
    gbn_receiver.close()

