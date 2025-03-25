import numpy as np
import time

class ProtocolHeader:
    def __init__(self):
        self.header_type = np.dtype([
            ('TimeStamp', np.uint64),
            ('MessageType', np.uint8),
            ('SequenceNumber', np.uint64),
            ('BodyLength', np.uint32)
        ])

    def get_header_message(self, timestamp, message_type, sequence_number, body_length):
        ret = np.array((timestamp, message_type, sequence_number, body_length), dtype=self.header_type)
        return ret
    
if __name__=="__main__":
    head_setter = ProtocolHeader()
    ret = head_setter.get_header_message(time.time_ns(), 1, 1, 0)
    print(ret)
    print(f"Size of ret: {ret.nbytes} bytes")
