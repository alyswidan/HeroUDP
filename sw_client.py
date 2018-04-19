from senders import StopAndWaitSender
from receivers import StopAndWaitReceiver


(file_name, server_ip, server_port) = input('give me the file name, ip and port of the server:\n').split()
SWSender = StopAndWaitSender(server_ip, server_port)
SWReceiver = StopAndWaitReceiver()
SWSender.send_data(bytes(file_name, encoding='ascii'))

init_packet, server_address = SWReceiver.receive()
number_of_packets = int(init_packet.data)
packets = []
for _ in range(number_of_packets):
    packet, _ = SWReceiver.receive()
    packets.append(packet)
    print(f'received packet with sequence number {packets[-1].seq_number}')
    print(f'with data {packets[-1].data}')

with open(f'{file_name}_client', 'wb+') as file:
    for packet in packets:
        file.write(bytes(packet.data, encoding='ascii'))

print('done writing file to disk')

# clientSocket.close()