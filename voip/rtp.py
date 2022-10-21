import ctypes
import struct

class RTPMessage():


    def __init__(self, **kwargs):
        self.mask = int(kwargs.get('mask', 0))
        self.timestamp = int(kwargs.get('timestamp', 0))
        self.ssrc = int(kwargs.get('ssrc', 0))
        self.csrc = int(kwargs.get('csrc', 0))
        self.extension = int(kwargs.get('extension', 0))

        if 'values' in kwargs:
            values = kwargs.get('values')
            assert(isinstance(values, bytes))
            assert(len(values) == 20)
            self.mask, self.timestamp, self.ssrc, self.csrc, \
            self.extension  = struct.unpack('IIIII', values)

    def from_bytes(values):
        return RTPMessage(values=values)

    def to_bytes(self):
        return struct.pack(
            'IIIII',
            self.mask, self.timestamp,
            self.ssrc, self.csrc,
            self.extension
            )

    @property
    def version(self):
        return (self.mask >> 30) & 0x0003

    @version.setter
    def version(self, value):
        version = (value & 0x0003) << 30 | (self.mask & 0x3fffffff)
        self.mask = version

    @property
    def padding(self):
        return (self.mask >> 29) & 0x0001

    @padding.setter
    def padding(self, value):
        pad = (value & 0x0001) << 29 | (self.mask & 0xdfffffff)
        self.mask = pad
    @property
    def has_extension(self):
        return (self.mask >> 28) & 0x0001

    @has_extension.setter
    def has_extension(self, value):
        ext = (value & 0x0001) << 28 | (self.mask & 0xefffffff)
        self.mask = ext

    @property
    def csrc_count(self):
        return (self.mask >> 24) & 0x000f

    @csrc_count.setter
    def csrc_count(self, value):
        csrc = (value & 0x000f) << 24 | (self.mask & 0xf0ffffff)
        self.mask = csrc

    @property
    def marker(self):
        return (self.mask >> 23) & 0x0001

    @marker.setter
    def marker(self, value):
        marker = (value & 0x0001) << 23 | (self.mask & 0xffefffff)
        self.mask = marker

    @property
    def payload_type(self):
        return (self.mask >> 16) & 0x007f

    @payload_type.setter
    def payload_type(self, value):
        pt = (value & 0x007f) << 16 | (self.mask & 0xff8fffff)
        self. mask = pt

    @property
    def sequence_number(self):
        return (self.mask & 0x0000ffff)

    @sequence_number.setter
    def sequence_number(self, value):
        self.mask = (value & 0xffff) | (self.mask & 0xffff0000)

