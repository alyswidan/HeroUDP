import struct
import base64

CHUNK_SIZE = 668

class AckPacket:
    def __init__(self, seq_number=0):
        self.check_sum = 0
        self.seq_number = seq_number
        self.format_str = '!HI'
        self.encoding = 'ascii'

    @classmethod
    def from_raw(cls, raw_packet):
        packet = cls()
        packet.check_sum, packet.seq_number = struct.unpack(packet.format_str, raw_packet)
        return packet

    def get_raw(self):
        self.raw = struct.pack(self.format_str, self.check_sum, self.seq_number)
        return self.raw

    def __str__(self):
        return f'Ack\n' + f'seq_num = {self.seq_number}\n'


class DataPacket:
    def __init__(self, data=bytes(0), seq_number=0):
        """
        :param data: type = bytes-like object
        :param seq_number: type = int
        """
        self.check_sum = 0
        self.data = data
        self.seq_number = seq_number
        self.len = len(data)
        self.raw = None
        self.format_str = f'!HHI{CHUNK_SIZE}s'
        self.encoding = 'ascii'
        self.raw = None



    @classmethod
    def from_raw(cls, raw_packet):
        """
        :param raw_packet: type=bytes, bytes array representing a packet
        :return packet:  type=DataPacket, conversion of raw bytes into an instance of DataPacket
        """
        packet = cls()
        packet.check_sum, packet.len, packet.seq_number, raw_data \
            = struct.unpack(packet.format_str, raw_packet)
        packet.data = base64.b64decode(raw_data)[0:packet.len]
        return packet

    def get_raw(self):
        """
        gets the raw bytes representation of the DataPacket and caches the raw bytes in self.raw
        :return: raw: type=bytes, if the bytes representation is cached return it else get it first
        """
        if self.raw is not None:
            return self.raw
        encoded_data = base64.b64encode(self.data)

        self.raw = struct.pack(self.format_str, self.check_sum, self.len,
                               self.seq_number, encoded_data)

        return self.raw

    def __str__(self):
        return f'data = {self.data}\n' + f'len = {self.len}\n' + f'seq_num = {self.seq_number}\n'


