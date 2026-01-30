class FieldComponent:
    def __init__(self, field_id: int, accumulate: bool, bits: int, scale: float, offset: float):
        self.field_id = field_id
        self.accumulate = accumulate
        self.bits = bits
        self.scale = scale
        self.offset = offset
