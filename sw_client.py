
from helpers import get_stdout_logger
import logging
import uuid

from packet import DataPacket
from stop_and_wait_receiver import StopAndWaitReceiver
from stop_and_wait_sender import StopAndWaitSender
from lossy_decorator import *

LOSS_PROB = 0.1
logger = get_stdout_logger('sw_client')

run_unique_id = uuid.uuid4().hex[0:6]
(file_name, server_ip, server_port) = input('give me the file name, ip and port of the server:\n').split()
server_port = int(server_port)
sw_sender = make_lossy_sender(StopAndWaitSender(server_ip, server_port),LOSS_PROB)
sw_receiver = StopAndWaitReceiver.from_sw_sender(sw_sender)

sw_sender.send_data(bytes(file_name, encoding='ascii'),run_unique_id,-1)
# logger.log(logging.INFO, 'done sending file name')

init_packet, _ = sw_receiver.receive()
# logger.log(logging.INFO, f'received {init_packet.data} as the number of packets')
number_of_packets = int(init_packet.data)
packets = []
for i in range(number_of_packets):
    packet, _ = sw_receiver.receive()
    packets.append(packet)

sw_sender.close()
sw_receiver.close()
with open(f'{file_name}_client_{run_unique_id}', 'wb+') as file:
    for packet in packets:
        file.write(packet.data)

logging.log(logging.INFO, 'done writing file to disk')
