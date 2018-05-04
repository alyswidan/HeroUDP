
import uuid

from helpers.logger_utils import get_stdout_logger
from receivers.stop_and_wait_receiver import StopAndWaitReceiver
from senders.stop_and_wait_sender import StopAndWaitSender
import logging

logger = get_stdout_logger('sw_client')

run_unique_id = uuid.uuid4().hex[0:6]
(file_name, server_ip, server_port) = input('give me the file name, ip and port of the server:\n').split()
server_port = int(server_port)
sw_sender = StopAndWaitSender(server_ip, server_port)
sw_receiver = StopAndWaitReceiver.from_sw_sender(sw_sender)

sw_sender.send_data(bytes(file_name, encoding='ascii'),run_unique_id,-1)

init_packet, _ = sw_receiver.receive()
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

logger.log(logging.INFO, 'done writing file to disk')
