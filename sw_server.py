from threading import Thread
from senders import StopAndWaitSender
from socket import *
from receivers import StopAndWaitReceiver

BUFFER_SIZE = 508
CHUNK_SIZE = 500
WELCOMING_PORT = 20000


def send_file(file_name, client_address):
    file_socket = socket(AF_INET, SOCK_DGRAM)
    SWsender = StopAndWaitSender(file_socket, client_address)

    # get the number of packets required to send the file
    bytes_in_file = os.stat(file_name).st_size
    number_of_packets = bytes_in_file // CHUNK_SIZE
    number_of_packets += 1 if number_of_packets % CHUNK_SIZE != 0 else 0

    SWsender.send_data(bytes(str(number_of_packets), encoding='ascii'))
    SWsender.call_from_above_cv.wait()

    with open(file_name, 'rb') as file:
        for _ in range(number_of_packets):
            data_chunk = file.read(CHUNK_SIZE)
            SWsender.send_data(data_chunk)
            SWsender.call_from_above_cv.wait()


client_threads = []
SWReceiver = StopAndWaitReceiver()
while 1:
    init_packet, client_address = SWReceiver.receive()
    file_name = init_packet.data
    print(f'client {client_address} requested {file_name}')
    client_threads.append(Thread(target=send_file, args=(file_name, client_address,)))
    client_threads[-1].daemon = True
    client_threads[-1].start()
