import struct


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
    def __init__(self, data='', seq_number=0):
        self.check_sum = 0
        self.data = data
        self.seq_number = seq_number
        self.len = len(data)
        self.raw = None
        self.format_str = '!HHI500s'
        self.encoding = 'ascii'


    @classmethod
    def from_raw(cls, raw_packet):
        packet = cls()
        packet.check_sum, packet.len, packet.seq_number, raw_data \
            = struct.unpack(packet.format_str, raw_packet)
        packet.data = raw_data.decode(packet.encoding)[0:packet.len]
        return packet

    def get_raw(self):
        self.raw = struct.pack(self.format_str, self.check_sum, self.len,
                               self.seq_number, self.data)

        return self.raw

    def __str__(self):
        return f'data = {self.data}\n' + f'len = {self.len}\n' + f'seq_num = {self.seq_number}\n'


def get_segments(data):
    segments = [data[i:min(len(data), i + 500)] for i in range(0, len(data), 500)]
    return segments

