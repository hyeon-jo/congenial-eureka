import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
import pickle
import boost.python as bp
import struct

@dataclass
class ProtocolHeader:
    """Base protocol header structure"""
    timestamp: np.uint64
    message_type: np.uint8
    sequence_number: np.uint64
    body_length: np.uint32

    def to_bytes(self) -> bytes:
        return struct.pack('<QIQI', 
            self.timestamp,
            self.message_type,
            self.sequence_number,
            self.body_length
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'ProtocolHeader':
        timestamp, message_type, sequence_number, body_length = struct.unpack('<QIQI', data)
        return cls(timestamp, message_type, sequence_number, body_length)

@dataclass
class LoggingMsg:
    """Structure for logging message"""
    header: ProtocolHeader
    data: Optional[np.ndarray] = None

@dataclass
class Header:
    """Header structure for data record configuration"""
    timestamp: np.uint64
    message_type: np.uint8
    sequence_number: np.uint64
    body_length: np.uint32

@dataclass
class LoggingFile:
    """Structure for logging file configuration"""
    id: np.uint32
    enable: str
    name_prefix: str
    name_subfix: str
    extension: str

@dataclass
class MetaData:
    """Structure for metadata"""
    data: Dict[str, str]
    issue: str

@dataclass
class DataRecordConfigMsg:
    """Main data record configuration message structure"""
    header: Header
    logging_directory_path: str
    logging_mode: np.uint32
    history_time: np.uint32
    follow_time: np.uint32
    split_time: np.uint32
    data_length: np.uint32
    logging_file_list: List[LoggingFile]
    meta_data: MetaData

@dataclass
class DataRecordViewerMsg:
    """Structure for data record viewer message"""
    header: Header
    register_num: str
    issue_log: str
    control_id: str

class DataRecordConfigMsgHandler:
    """Handler class for DataRecordConfigMsg operations"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataRecordConfigMsgHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.logging_msg_queue = []
        self.data_record_config_msg = DataRecordConfigMsg(
            header=Header(0, 0, 0, 0),
            logging_directory_path="",
            logging_mode=np.uint32(0),
            history_time=np.uint32(0),
            follow_time=np.uint32(0),
            split_time=np.uint32(0),
            data_length=np.uint32(0),
            logging_file_list=[],
            meta_data=MetaData({}, "")
        )
        self.data_record_viewer_msg = DataRecordViewerMsg(
            header=Header(0, 0, 0, 0),
            register_num="",
            issue_log="",
            control_id=""
        )

    def set_data_length(self, data_length: np.uint32):
        self.data_record_config_msg.data_length = data_length

    def get_data_length(self) -> np.uint32:
        return self.data_record_config_msg.data_length

    def set_data(self, data: List[LoggingFile]):
        self.data_record_config_msg.logging_file_list = data

    def get_data(self) -> DataRecordConfigMsg:
        return self.data_record_config_msg

    def get_meta_data(self) -> MetaData:
        return self.data_record_config_msg.meta_data

    def set_logging_directory_path(self, path: str):
        self.data_record_config_msg.logging_directory_path = path

    def get_logging_directory_path(self) -> str:
        return self.data_record_config_msg.logging_directory_path

    def set_logging_mode(self, logging_mode: np.uint32):
        self.data_record_config_msg.logging_mode = logging_mode

    def get_logging_mode(self) -> np.uint8:
        return np.uint8(self.data_record_config_msg.logging_mode)

    def set_history_time(self, history_time: np.uint32):
        self.data_record_config_msg.history_time = history_time

    def get_history_time(self) -> np.uint32:
        return self.data_record_config_msg.history_time

    def set_follow_time(self, follow_time: np.uint32):
        self.data_record_config_msg.follow_time = follow_time

    def get_follow_time(self) -> np.uint32:
        return self.data_record_config_msg.follow_time

    def set_split_time(self, split_time: np.uint32):
        self.data_record_config_msg.split_time = split_time

    def get_split_time(self) -> np.uint32:
        return self.data_record_config_msg.split_time

    def set_msg_type(self, message_type: np.uint8):
        self.data_record_config_msg.header.message_type = message_type

    def get_msg_type(self) -> np.uint8:
        return np.uint8(self.data_record_config_msg.header.message_type)

    def get_logging_file(self) -> List[LoggingFile]:
        return self.data_record_config_msg.logging_file_list

    def get_package_size(self) -> np.uint32:
        """Calculate the total package size including header and body"""
        header_size = 21  # Size of ProtocolHeader (8 + 4 + 8 + 4 bytes)
        body_size = self.calculate_body_size()
        return np.uint32(header_size + body_size)

    def calculate_body_size(self) -> int:
        """Calculate the size of the message body"""
        # This should match the C++ server's serialization format
        size = 0
        size += len(self.data_record_config_msg.logging_directory_path.encode('utf-8')) + 4
        size += 4  # logging_mode
        size += 4  # history_time
        size += 4  # follow_time
        size += 4  # split_time
        size += 4  # data_length
        size += 4  # logging_file_list size
        for file in self.data_record_config_msg.logging_file_list:
            size += 4  # id
            size += len(file.enable.encode('utf-8')) + 4
            size += len(file.name_prefix.encode('utf-8')) + 4
            size += len(file.name_subfix.encode('utf-8')) + 4
            size += len(file.extension.encode('utf-8')) + 4
        size += 4  # meta_data size
        size += len(str(self.data_record_config_msg.meta_data).encode('utf-8')) + 4
        return size

    def make_package(self, msg: DataRecordConfigMsg) -> bytes:
        """Serialize the message into bytes"""
        # First serialize the header
        header_bytes = msg.header.to_bytes()
        
        # Then serialize the body
        body_bytes = self.serialize_body(msg)
        
        # Combine header and body
        return header_bytes + body_bytes

    def serialize_body(self, msg: DataRecordConfigMsg) -> bytes:
        """Serialize the message body"""
        body_data = bytearray()
        
        # Serialize logging_directory_path
        path_bytes = msg.logging_directory_path.encode('utf-8')
        body_data.extend(struct.pack('<I', len(path_bytes)))
        body_data.extend(path_bytes)
        
        # Serialize numeric fields
        body_data.extend(struct.pack('<IIIII',
            msg.logging_mode,
            msg.history_time,
            msg.follow_time,
            msg.split_time,
            msg.data_length
        ))
        
        # Serialize logging_file_list
        body_data.extend(struct.pack('<I', len(msg.logging_file_list)))
        for file in msg.logging_file_list:
            body_data.extend(struct.pack('<I', file.id))
            
            # Serialize string fields
            for field in [file.enable, file.name_prefix, file.name_subfix, file.extension]:
                field_bytes = field.encode('utf-8')
                body_data.extend(struct.pack('<I', len(field_bytes)))
                body_data.extend(field_bytes)
        
        # Serialize meta_data
        meta_data_str = str(msg.meta_data)
        meta_bytes = meta_data_str.encode('utf-8')
        body_data.extend(struct.pack('<I', len(meta_bytes)))
        body_data.extend(meta_bytes)
        
        return bytes(body_data)

    def parsing_data(self, data: bytes) -> DataRecordConfigMsg:
        """Deserialize the message from bytes"""
        # First parse the header
        header = ProtocolHeader.from_bytes(data[:21])
        
        # Then parse the body
        body_data = data[21:]
        msg = self.deserialize_body(body_data)
        msg.header = header
        return msg

    def deserialize_body(self, data: bytes) -> DataRecordConfigMsg:
        """Deserialize the message body"""
        offset = 0
        
        # Deserialize logging_directory_path
        path_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        logging_directory_path = data[offset:offset+path_len].decode('utf-8')
        offset += path_len
        
        # Deserialize numeric fields
        logging_mode, history_time, follow_time, split_time, data_length = struct.unpack('<IIIII', data[offset:offset+20])
        offset += 20
        
        # Deserialize logging_file_list
        file_list_size = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        logging_file_list = []
        
        for _ in range(file_list_size):
            file_id = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            # Deserialize string fields
            strings = []
            for _ in range(4):  # enable, name_prefix, name_subfix, extension
                str_len = struct.unpack('<I', data[offset:offset+4])[0]
                offset += 4
                string_value = data[offset:offset+str_len].decode('utf-8')
                offset += str_len
                strings.append(string_value)
            
            logging_file_list.append(LoggingFile(
                id=file_id,
                enable=strings[0],
                name_prefix=strings[1],
                name_subfix=strings[2],
                extension=strings[3]
            ))
        
        # Deserialize meta_data
        meta_len = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        meta_data_str = data[offset:offset+meta_len].decode('utf-8')
        
        # Create and return the message
        return DataRecordConfigMsg(
            header=Header(0, 0, 0, 0),  # Will be set by caller
            logging_directory_path=logging_directory_path,
            logging_mode=np.uint32(logging_mode),
            history_time=np.uint32(history_time),
            follow_time=np.uint32(follow_time),
            split_time=np.uint32(split_time),
            data_length=np.uint32(data_length),
            logging_file_list=logging_file_list,
            meta_data=MetaData({"data": {}, "issue": ""})  # Simplified meta_data
        )

    def get_logging_msg(self, logging_msg: LoggingMsg) -> np.uint8:
        if self.logging_msg_queue:
            logging_msg = self.logging_msg_queue.pop(0)
            return np.uint8(1)
        return np.uint8(0)

    def set_logging_msg(self, msg_type: int, data: Optional[np.ndarray] = None, data_size: np.uint32 = 0):
        header = ProtocolHeader(0, msg_type, 0, data_size)
        logging_msg = LoggingMsg(header, data)
        self.logging_msg_queue.append(logging_msg) 