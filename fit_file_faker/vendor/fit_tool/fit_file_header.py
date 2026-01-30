import struct

from fit_file_faker.vendor.fit_tool.utils.crc import crc16


class ProtocolVersion:
    def __init__(self, major: int, minor: int):
        self.major = major
        self.minor = minor

    def to_bytes(self) -> bytes:
        return struct.pack('B', (self.major << 4) | self.minor)

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes):
        value = bytes_buffer[0]
        major = value >> 4
        minor = value & 0x0f
        return ProtocolVersion(major, minor)

    def __str__(self):
        return f'{self.major}.{self.minor}'


class ProfileVersion:
    MAJOR_SCALE = 100

    def __init__(self, major: int, minor: int):
        self.major = major
        self.minor = minor

    def to_bytes(self) -> bytes:
        return struct.pack('<H', self.version_code)

    @property
    def version_code(self):
        return self.major * ProfileVersion.MAJOR_SCALE + self.minor

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes):
        value, = struct.unpack('<H', bytes_buffer[0:2])
        major = value // ProfileVersion.MAJOR_SCALE
        minor = value % ProfileVersion.MAJOR_SCALE
        return ProfileVersion(major, minor)

    def __str__(self):
        return f'{self.major}.{self.minor}'


DEFAULT_PROTOCOL_VERSION = ProtocolVersion(2, 3)
DEFAULT_PROFILE_VERSION = ProfileVersion(21, 60)


class FitFileHeader:
    def __init__(self, records_size: int, protocol_version: ProtocolVersion = None,
                 profile_version: ProfileVersion = None, crc: int = None, gen_crc: bool = False):
        self.records_size = records_size
        self.protocol_version = protocol_version if protocol_version else DEFAULT_PROTOCOL_VERSION
        self.profile_version = profile_version if profile_version else DEFAULT_PROFILE_VERSION

        # crc16 of header bytes 0-11
        #
        # By including the CRC in the header you effectively reset the CRC for the
        # file, (when you CRC-16 a value with itself the CRC returned is 0)
        if crc is not None:
            self.crc = crc
        elif gen_crc:
            self.crc = FitFileHeader.generate_crc(self.protocol_version, self.profile_version, self.records_size)
        else:
            self.crc = None

    @classmethod
    def generate_crc(cls, protocol_version, profile_version, records_size):
        bytes_buffer = struct.pack('B', 14)
        bytes_buffer += protocol_version.to_bytes()
        bytes_buffer += profile_version.to_bytes()
        bytes_buffer += struct.pack('<I', records_size)
        bytes_buffer += b'.FIT'

        return crc16(bytes_buffer)

    @property
    def size(self) -> int:
        if self.crc is not None:
            return 14
        else:
            return 12

    def to_bytes(self) -> bytes:

        bytes_buffer = struct.pack('B', self.size)
        bytes_buffer += self.protocol_version.to_bytes()
        bytes_buffer += self.profile_version.to_bytes()
        bytes_buffer += struct.pack('<I', self.records_size)
        bytes_buffer += b'.FIT'

        if self.crc is not None:
            bytes_buffer += struct.pack('<H', self.crc)

        return bytes_buffer

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes):
        offset = 0
        size, = struct.unpack('B', bytes_buffer[0:1])
        if size != len(bytes_buffer):
            raise Exception(f'Size {size} does not match bytes length: ${len(bytes_buffer)}')
        offset += 1

        protocol_version = ProtocolVersion.from_bytes(bytes_buffer[offset: offset + 1])
        offset += 1

        profile_version = ProfileVersion.from_bytes(bytes_buffer[offset: offset + 2])
        offset += 2

        records_size, = struct.unpack('<I', bytes_buffer[offset:offset + 4])
        offset += 4

        # .FIT
        tag_value, = struct.unpack('4s', bytes_buffer[offset:offset + 4])
        offset += 4
        if tag_value != b'.FIT':
            raise Exception('".FIT" not in header.')

        crc = None
        if len(bytes_buffer) == 14:
            crc, = struct.unpack('<H', bytes_buffer[offset:offset + 2])

        return cls(protocol_version=protocol_version,
                   profile_version=profile_version,
                   records_size=records_size,
                   crc=crc)
