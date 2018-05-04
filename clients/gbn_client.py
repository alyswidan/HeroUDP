from receivers.gbn_receiver import GoBackNReceiver
from senders.gbn_sender import GoBackNSender

def start_client(server_ip, server_port, file_name, window_size=15, loss_prob=0.2):
    gbn_sender = GoBackNSender(server_ip, server_port)
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

    with open(f'{file_name}_{client_id}', 'wb+') as file:
        for i in range(number_of_packets):
            file.write(gbn_receiver.get_packet().data)
    gbn_receiver.close()

start_client('127.0.0.1',3000, '../test_files/medium_pdf_test',loss_prob=0.2)
