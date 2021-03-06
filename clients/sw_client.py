import uuid

from helpers.general_helpers import timeit
from helpers.logger_utils import get_stdout_logger
from receivers.stop_and_wait_receiver import StopAndWaitReceiver
from senders.stop_and_wait_sender import StopAndWaitSender
import logging
@timeit('sw_client')
def start_client(other_ip, other_port, file_name, **kwargs):

    logger = get_stdout_logger('sw_client')
    sw_sender = StopAndWaitSender(other_ip, other_port)
    sw_receiver = StopAndWaitReceiver.from_sw_sender(sw_sender)
    sw_sender.send_data(bytes(file_name, encoding='ascii'),-1,-1)

    id_pkt,_ = sw_receiver.receive() # get an id from the server
    client_id = str(id_pkt.data,'ascii')

    count_pkt,_ = sw_receiver.receive() # get the number of packets in the file
    number_of_packets = int(count_pkt.data)


    for i in range(number_of_packets):
        with open(f'HeroUDP/client_output/files/{file_name}_{client_id}_sw','wb+') as file:
            packet, _ = sw_receiver.receive()
            file.write(packet.data)

    sw_sender.close()
    sw_receiver.close()

    logger.log(logging.INFO, 'done writing file to disk')


