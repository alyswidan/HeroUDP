from socket import *
from packet import *
import logging

from senders import UDTSender

logging.basicConfig(format='%(asctime)s -> %(levelname) : %(message)s')
BUFFER_SIZE = 508


clientSocket = socket(AF_INET, SOCK_DGRAM)
(file_name, server_ip, server_port) = input('give me the file name, ip and port of the server:\n').split()
udt_sender = UDTSender(clientSocket, (server_ip, int(server_port)))
udt_sender.send_data(bytes(file_name, encoding='ascii'))

raw_init_packet, server_address = clientSocket.recvfrom(BUFFER_SIZE)
init_packet = DataPacket.from_raw(raw_init_packet)
number_of_packets = int(init_packet.data)
packets = []
for _ in range(number_of_packets):
    raw_packet, server_address = clientSocket.recvfrom(BUFFER_SIZE)
    packets.append(DataPacket.from_raw(raw_packet))
    print(f'received packet with sequence number {packets[-1].seq_number} with data {packets[-1].data}')

print('received all')
p = AckPacket(19)
print(type(p))

with open(f'{file_name}_client', 'wb+') as file:
    for packet in packets:
        file.write(bytes(packet.data, encoding='ascii'))

print('done writing file to disk')

clientSocket.close()
