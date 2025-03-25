# TCP/IP Control Application

This project consists of a GUI control application and backend processes that communicate via TCP/IP.

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
```

2. Activate virtual environment:
```bash
# On Linux/Mac:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start two backend processes in separate terminals (make sure venv is activated in each):
```bash
# Terminal 1
python backend_process.py 12345

# Terminal 2
python backend_process.py 12346
```

2. Start the control application in another terminal:
```bash
python control_app.py
```

## Features

- Control application with two buttons:
  - Toggle button: Sends START/END messages
  - Event button: Sends EVENT message (disabled for 30 seconds after use)
- Backend processes:
  - Listen on specified ports
  - Handle START, END, and EVENT messages
  - Show connection status and message processing 