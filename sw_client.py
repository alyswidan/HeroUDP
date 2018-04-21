
from helpers import get_stdout_logger
import logging

from stop_and_wait_receiver import StopAndWaitReceiver
from stop_and_wait_sender import StopAndWaitSender

logger = get_stdout_logger()


(file_name, server_ip, server_port) = input('give me the file name, ip and port of the server:\n').split()
server_port = int(server_port)
sw_sender = StopAndWaitSender(server_ip, server_port)
sw_receiver = StopAndWaitReceiver.from_sw_sender(sw_sender)

sw_sender.send_data(bytes(file_name, encoding='ascii'))
logger.log(logging.INFO, 'done sending file name')

init_packet, _ = sw_receiver.receive()
logger.log(logging.INFO, f'received {init_packet.data} as the number of packets')
number_of_packets = int(init_packet.data)
packets = []
for _ in range(number_of_packets):
    packet, _ = sw_receiver.receive()
    packets.append(packet)
    logger.log(logging.INFO, f'received packet with sequence number {packets[-1].seq_number}'
                             f' and data {" ".join(packets[-1].data.split()[0:4])}...')

with open(f'{file_name}_client', 'wb+') as file:
    for packet in packets:
        file.write(bytes(packet.data, encoding='ascii'))

logging.log(logging.INFO, 'done writing file to disk')
