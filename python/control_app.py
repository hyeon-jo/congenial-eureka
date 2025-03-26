import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                           QWidget, QMessageBox, QLabel, QGridLayout, QLineEdit,
                           QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QTimer
import socket
import threading
import time
from tcp_common import ProtocolHeader
import numpy as np
import boost.python as bp
from data_record_config_msg import DataRecordConfigMsgHandler, DataRecordConfigMsg, Header


class ControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control Panel")
        
        # TCP/IP settings for two backends
        self.backends = [
            {"host": "localhost", "ports": [9090, 9091], "name": "Backend 1", 
             "ready": False, "sockets": [None, None]},
            {"host": "localhost", "ports": [9092, 9093], "name": "Backend 2",
             "ready": False, "sockets": [None, None]}
        ]
        self.is_toggle_on = False
        self.event_sent = False
        self.message_counter = 0
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)  # Add more space between groups
        
        # Create IP configuration group
        config_group = QGroupBox("Backend Configuration")
        config_layout = QGridLayout()
        config_layout.setSpacing(10)  # Add space between elements
        
        # Create input fields for each backend
        self.ip_inputs = []
        
        for i, backend in enumerate(self.backends):
            # IP input
            ip_label = QLabel(f"{backend['name']} IP:")
            ip_label.setStyleSheet("font-size: 32px;")
            ip_input = QLineEdit(backend['host'])
            ip_input.setPlaceholderText("Enter IP address")
            ip_input.setStyleSheet("font-size: 32px; padding: 5px;")
            config_layout.addWidget(ip_label, i, 0)
            config_layout.addWidget(ip_input, i, 1)
            self.ip_inputs.append(ip_input)
            
            # Port labels (fixed ports)
            port_label = QLabel(f"Ports: {backend['ports'][0]}, {backend['ports'][1]}")
            port_label.setStyleSheet("font-size: 32px;")
            config_layout.addWidget(port_label, i, 2)
        
        # Add apply button
        self.apply_btn = QPushButton("Apply Configuration")
        self.apply_btn.setMinimumSize(200, 50)
        self.apply_btn.clicked.connect(self.apply_configuration)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                font-size: 32px;
                font-weight: bold;
                padding: 5px;
                background-color: #008CBA;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #007399;
            }
        """)
        config_layout.addWidget(self.apply_btn, len(self.backends), 0, 1, 4)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # Create control group
        control_group = QGroupBox("Control Panel")
        control_layout = QGridLayout()
        
        # Create status labels
        self.status_labels = []
        for i, backend in enumerate(self.backends):
            label = QLabel(f"{backend['name']}: Not Connected")
            label.setStyleSheet("color: red; font-size: 32px;")
            control_layout.addWidget(label, 0, i, alignment=Qt.AlignCenter)
            self.status_labels.append(label)
        
        # Create buttons with larger font
        self.toggle_btn = QPushButton("Start")
        self.toggle_btn.setMinimumSize(200, 50)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                font-size: 32px;
                font-weight: bold;
                padding: 5px;
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_action)
        
        self.event_btn = QPushButton("Send Event")
        self.event_btn.setMinimumSize(200, 50)
        self.event_btn.setStyleSheet("""
            QPushButton {
                font-size: 32px;
                font-weight: bold;
                padding: 5px;
                background-color: #008CBA;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #007399;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.event_btn.clicked.connect(self.send_event)
        
        # Add buttons to layout
        control_layout.addWidget(self.toggle_btn, 1, 0, 1, 2, alignment=Qt.AlignCenter)
        control_layout.addWidget(self.event_btn, 2, 0, 1, 2, alignment=Qt.AlignCenter)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Set initial window size and position
        self.setMinimumSize(1200, 800)  # Increased window size to accommodate larger fonts
        self.resize(1200, 800)
        self.center_window()
        
        # Create timer for re-enabling event button
        self.timer = QTimer()
        self.timer.timeout.connect(self.enable_event_button)
        
        # Create timer for checking backend status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.connect_to_server)
        self.status_timer.start(1000)  # Check every 1 second
        
        # Set window style
        self.setStyleSheet("""
            QGroupBox {
                font-size: 32px;
                font-weight: bold;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #999;
                border-radius: 3px;
            }
        """)
        
        self.event_btn.setEnabled(True)  # Enable event button in initial state
        
    def connect_to_server(self):
        all_connected = True
        message_handler = DataRecordConfigMsgHandler()
        
        # 각 백엔드에 대해
        for i, backend in enumerate(self.backends):
            prev_counter = self.message_counter
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect((backend["host"], backend["ports"][0]))

                # First message (MessageType 1)
                self.message_counter += 1
                first_msg = Header(time.time_ns(), 1, self.message_counter, 0)
                s.sendall(first_msg.tobytes())
                response_data = s.recv(21)
                response = Header.from_bytes(response_data)
                if response.message_type != 2:
                    raise Exception(f"Expected MessageType 2, got {response.message_type}")
                
                # Second message (MessageType 3)
                self.message_counter += 1
                second_msg = Header(time.time_ns(), 3, self.message_counter, 0)
                s.sendall(second_msg.tobytes())
                response_data = s.recv(21)
                response = Header.from_bytes(response_data)
                if response.message_type != 4:
                    raise Exception(f"Expected MessageType 2, got {response.message_type}")

                backend["ready"] = True
                self.status_labels[i].setText(f"{backend['name']}: Connected")
                self.status_labels[i].setStyleSheet("color: green; font-size: 32px;")
                
            except Exception as e:
                print(f"Error with {backend['name']}:{backend['ports'][0]}: {e}")
                all_connected = False
                self.status_labels[i].setText(f"{backend['name']}: Not Connected")
                self.status_labels[i].setStyleSheet("color: red; font-size: 32px;")
                if 's' in locals():
                    s.close()
                self.message_counter = prev_counter
                continue
            
        if all_connected and all(backend["ready"] for backend in self.backends):
            self.status_timer.stop()
            self.event_sent = False
            self.event_btn.setEnabled(True)
            self.toggle_btn.setEnabled(True)
            print("All backends connected successfully")
            return True
        
        return False
        
    def apply_configuration(self):
        for i, backend in enumerate(self.backends):
            try:
                # Validate IP
                ip = self.ip_inputs[i].text().strip()
                if not ip:
                    raise ValueError(f"{backend['name']}: IP address cannot be empty")
                
                # Update backend configuration
                self.backends[i]['host'] = ip
                
            except ValueError as e:
                QMessageBox.warning(self, "Configuration Error", str(e))
                return
        
        QMessageBox.information(self, "Success", "Configuration applied successfully")

    def center_window(self):
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
        
    def set_message_content(self, message):
        message.BodyLength = 0
        return message

    def send_tcp_message(self, start=True):
        message_handler = DataRecordConfigMsgHandler()
        
        if start:
            self.message_counter += 1
            config_msg = DataRecordConfigMsg(
                header=Header(time.time_ns(), 19, self.message_counter, 0),
                logging_directory_path="",
                logging_mode=np.uint32(0),
                history_time=np.uint32(0),
                follow_time=np.uint32(0),
                split_time=np.uint32(0),
                data_length=np.uint32(0),
                logging_file_list=[],
                meta_data={"data": {}, "issue": ""}
            )
        else:
            self.message_counter += 1
            config_msg = DataRecordConfigMsg(
                header=Header(time.time_ns(), 21, self.message_counter, 0),
                logging_directory_path="",
                logging_mode=np.uint32(0),
                history_time=np.uint32(0),
                follow_time=np.uint32(0),
                split_time=np.uint32(0),
                data_length=np.uint32(0),
                logging_file_list=[],
                meta_data={"data": {}, "issue": ""}
            )
            
        # Calculate body length
        body_size = message_handler.calculate_body_size()
        config_msg.header.body_length = np.uint32(body_size)
            
        serialized_data = message_handler.make_package(config_msg)
        
        for backend in self.backends:
            if backend["ready"]:
                backend["sockets"][1].sendall(serialized_data)
    
    def toggle_action(self):
        if not self.is_toggle_on:  # Sending START
            success, failed_backends = self.send_tcp_message()
            if success:
                self.toggle_btn.setText("End")
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 32px;
                        font-weight: bold;
                        padding: 5px;
                        background-color: #ff9999;
                        color: white;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #ff8080;
                    }
                """)
                self.is_toggle_on = True
                self.event_btn.setEnabled(False)  # Disable event button after successful START
            else:
                # If START fails, notify other backend
                if len(failed_backends) < len(self.backends):
                    failure_message = f"CONNECTION_FAIL:{','.join(failed_backends)}"
                    self.send_tcp_message(failure_message)
                
                self.toggle_btn.setText("Start")
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 32px;
                        font-weight: bold;
                        padding: 5px;
                        background-color: #4CAF50;
                        color: white;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                self.is_toggle_on = False
                self.event_btn.setEnabled(True)  # Enable event button if START fails
        else:  # Sending END
            success, _ = self.send_tcp_message(start=False)
            if success:
                self.toggle_btn.setText("Start")
                self.toggle_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 32px;
                        font-weight: bold;
                        padding: 5px;
                        background-color: #4CAF50;
                        color: white;
                        border-radius: 5px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                self.is_toggle_on = False
                self.event_btn.setEnabled(True)  # Enable event button when END is sent

    def send_event(self):
        # 이벤트 전송 로직 구현 필요
        pass
    
    def enable_event_button(self):
        self.event_btn.setEnabled(True)
        self.timer.stop()

    def closeEvent(self, event):
        # 프로그램 종료 시 모든 소켓 정리
        for backend in self.backends:
            for socket in backend["sockets"]:
                if socket is not None:
                    try:
                        socket.close()
                    except:
                        pass
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ControlApp()
    window.show()
    sys.exit(app.exec_()) 