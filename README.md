# Raspyjack C2 - Command & Control Center

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A graphical Command and Control (C2) server and client designed for managing remote Raspyjack devices. This system allows an operator to register multiple devices, send shell commands, and view the results in a clean, modern desktop application.

## Features

- **Centralized Device Management:** View all registered devices and their status in one place.
- **Desktop GUI Control Panel:** A user-friendly control panel built with CustomTkinter.
- **Remote Command Execution:** Send any shell command to a connected device.
- **Real-time Results:** View the `stdout` and `stderr` from executed commands directly in the GUI.
- **Lightweight Python Client:** A simple and portable client script for the Raspyjack.
- **FastAPI Backend:** A high-performance, asynchronous backend API to handle communication.

## Architecture

The system consists of three main components that work together:

```
+-----------------+      +----------------------+      +--------------------+
| Raspyjack Client|      |     C2 API Server    |      |   GUI Control Panel|
| (on Raspyjack)  |----->| (FastAPI + SQLite)   |<-----|   (CustomTkinter)  |
+-----------------+      +----------------------+      +--------------------+
       |                                                       ^
       | polls for commands, sends results                     | issues commands,
       |                                                       | views results
       +-------------------------------------------------------+
```

## Getting Started

Follow these instructions to set up and run the C2 server and deploy a client.

### 1. Server Setup (Your Computer)

The server consists of the backend API and the GUI control panel.

**Prerequisites:**
- Python 3.10+
- A display environment for the GUI (i.e., a desktop, not a headless server)

**Installation:**
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/wickednull/raspyC2
    cd RaspyjackC2
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

**Running the Application:**
The entire application (backend API and GUI) can be started with a single command:
  ```bash
  python raspyC2.py
  ```
This will launch the FastAPI backend in a separate process and then open the GUI control panel. When you close the GUI, the backend server will automatically shut down.

### 2. Client Setup (on the Raspyjack)

Deploy the client to your Raspyjack device.

**Prerequisites:**
- Python 3
- `pip` for Python 3
- `requests` library (and optionally `Pillow` and `pyscreenshot` for screen capture functionality)

**Installation:**
1.  **Transfer the entire `RaspyjackC2` project directory** to your Raspyjack. For the systemd service to function correctly, it is recommended to place it in `/root/Raspyjack`.
    ```bash
    # Example using scp from your computer
    scp -r /path/to/RaspyjackC2 pi@<your-raspyjack-ip>:/root/Raspyjack
    ```
2.  **SSH into your Raspyjack** and install the required dependencies:
    ```bash
    ssh pi@<your-raspyjack-ip>
    # Navigate to the client directory
    cd /root/Raspyjack
    pip3 install requests Pillow pyscreenshot
    ```
3.  **Install as a Systemd Service (Recommended for Production):**
    This will set up the client to run automatically on boot and restart if it crashes.
    ```bash
    sudo python3 c2_client/client.py install --c2-url http://<your-server-ip>:8000
    ```
    Replace `<your-server-ip>` with the local IP address of the computer running the C2 server.
    
    After installation, you can check the service status and logs:
    ```bash
    sudo systemctl status raspyjack-client
    journalctl -u raspyjack-client -f
    ```

**Running the Client (for Testing/Manual Use):**
If you prefer to run the client manually without installing it as a service, use the following command:
  ```bash
  python3 c2_client/client.py --name <unique-device-name> --c2-url http://<your-server-ip>:8000
  ```
  Replace `<unique-device-name>` with a name for your device and `<your-server-ip>` with the local IP address of the computer running the C2 server.
  The device will now appear in the GUI control panel on your server machine.

## Technology Stack

- **Backend:** FastAPI, Uvicorn, SQLAlchemy
- **GUI:** CustomTkinter
- **Database:** SQLite
- **Client:** Python standard libraries, Requests

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
