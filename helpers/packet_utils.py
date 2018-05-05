import struct


def compute_checksum(data_bytes):
    sum0,sum1 = 0,0
    for byte in data_bytes:
        sum0 = (sum0 + byte)%255
        sum1 = (sum0 + sum1) % 255
    # print(f'check sum = {hex(sum1<<8 | sum0)}')
    return sum1<<8 | sum0

def get_checksum_bytes(data_bytes):
    cks = compute_checksum(data_bytes)
    sum0 = cks & 0x00FF
    sum1 = (cks & 0xFF00)>>8
    sumb0 = 255 - ((sum0 + sum1)%255)
    sumb1 = 255 - ((sum0 + sumb0)%255)
    # print(f'check sum bytes = {hex(sumb1<<8 | sumb0)}')
    return sumb1<<8 | sumb0

def is_corrupted_packet(raw_packet):
    # logger.debug(f'check sum of raw packet = {compute_checksum(raw_packet[2:])}')
    # logger.debug(f'checksum in packet = {struct.unpack("!H", raw_packet[0:2])[0]}')

    print(compute_checksum(raw_packet[2:]) != struct.unpack('!H', raw_packet[0:2])[0])

    return compute_checksum(raw_packet[2:]) != struct.unpack('!H', raw_packet[0:2])[0]

def no_checksum_format(packet_format):
    return packet_format.replace('!H','!')

def create_checksum_packet(packet_format, *packet_fields):
    checksum_less_raw = struct.pack(no_checksum_format(packet_format), *packet_fields)
    # print(f'raw no cks = {checksum_less_raw}')
    raw = struct.pack(packet_format, compute_checksum(checksum_less_raw), *packet_fields)
    # print(f'raw={raw}')

    return raw