from fit_file_faker.vendor.fit_tool.endian import Endian


class Message:

    def __init__(self, local_id: int = 0, global_id: int = 0, size: int = 0, endian: Endian = Endian.LITTLE):
        # ID that provides an association between the definition message,
        # data message and the FIT message in the Global FIT Profile.
        self.local_id = local_id

        # ID of the FIT message in the Global FIT Profile.
        self.global_id = global_id
        self.endian = endian
        self.size = size

    def to_bytes(self) -> bytes:
        raise Exception('Not implemented')

    def to_row(self) -> list:
        raise Exception('Not implemented')
