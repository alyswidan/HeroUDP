import struct
import base64
from helpers.logger_utils import get_stdout_logger
from helpers.packet_utils import is_corrupted_packet, no_checksum_format, compute_checksum

CHUNK_SIZE = 668 # this is the size of 500 bytes after base64 encoding
logger = get_stdout_logger('packet','DEBUG')


class AckPacket:
    def __init__(self, seq_number=0, checksum=0):
        self.check_sum = checksum
        self.seq_number = seq_number
        self.packet_format = '!HI'
        self.encoding = 'ascii'

    def compute_checksum(self):
        checksum_less_raw = struct.pack(no_checksum_format(self.packet_format),self.seq_number)

        self.check_sum = compute_checksum(checksum_less_raw)

    @classmethod
    def from_raw(cls, raw_packet):

        packet = cls()
        if is_corrupted_packet(raw_packet):
            logger.error('corrupt packet')
            return None

        packet.check_sum, packet.seq_number = struct.unpack(packet.packet_format, raw_packet)
        return packet

    def get_raw(self):
        raw = struct.pack(self.packet_format, self.check_sum, self.seq_number)
        return raw

    def __str__(self):
        return f'Ack\n' + f'seq_num = {self.seq_number}\n'


class DataPacket:
    def __init__(self, data=bytes(0), seq_number=0, check_sum=0):
        """
        :param data: type = bytes-like object
        :param seq_number: type = int
        """

        self.data = data
        self.seq_number = seq_number
        self.len = len(data)
        self.raw = None
        self.packet_format = f'!HHI{CHUNK_SIZE}s'
        self.encoding = 'ascii'
        self.check_sum = check_sum


    def compute_checksum(self):

        checksum_less_raw = struct.pack(no_checksum_format(self.packet_format),
                                        self.len, self.seq_number,base64.b64encode(self.data))

        self.check_sum = compute_checksum(checksum_less_raw)

    @classmethod
    def from_raw(cls, raw_packet):
        """
        :param raw_packet: type=bytes, bytes array representing a packet
        :return packet:  type=DataPacket, conversion of raw bytes into an instance of DataPacket
        """

        packet = cls()

        if is_corrupted_packet(raw_packet):

            return None


        packet.check_sum, packet.len, packet.seq_number, raw_data \
            = struct.unpack(packet.packet_format, raw_packet)
        packet.data = base64.b64decode(raw_data)[0:packet.len]
        return packet



    def get_raw(self):
        """
        gets the raw bytes representation of the DataPacket and caches the raw bytes in self.raw
        :return: raw: type=bytes, if the bytes representation is cached return it else get it first
        """

        encoded_data = base64.b64encode(self.data)
        raw = struct.pack(self.packet_format, self.check_sum, self.len, self.seq_number, encoded_data)
        return raw


    def __str__(self):
        return f'data = {self.data}, ' + f'len = {self.len}, ' + f'seq_num = {self.seq_number}'


