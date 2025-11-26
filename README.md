# Raspyjack C2 - Command & Control Center
![image](https://github.com/user-attachments/assets/1087fdf3-a675-4554-89cc-74fe35348fa5)

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
    git clone https://github.com/wickednull/raspyC2.git
    cd raspyC2
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

**Running the Server:**
The server requires two processes to be running in separate terminals.

- **Terminal 1: Run the Backend API:**
  ```bash
  python -m uvicorn c2_server.main:app --reload
  ```
- **Terminal 2: Run the GUI Control Panel:**
  ```bash
  python gui_app.py
  ```

### 2. Client Setup (on the Raspyjack)

Deploy the client to your Raspyjack device.

**Prerequisites:**
- Python 3
- `pip` for Python 3

**Installation:**
1.  **Transfer the `c2_client` directory** to your Raspyjack's home directory (`/home/pi`). You can use `scp` for this.

2.  **SSH into your Raspyjack** and install the required dependency:
    ```bash
    ssh pi@<your-raspyjack-ip>
    pip3 install requests
    ```

3.  **Configure the Client:**
    - On the Raspyjack, open the client script for editing: `nano c2_client/client.py`
    - Find the line: `C2_URL = "http://127.0.0.1:8000/api"`
    - Change `127.0.0.1` to the **local IP address of the computer running the server**.
    - Save the file (`Ctrl+X`, `Y`, `Enter`).

**Running the Client:**
- From your Raspyjack's terminal, run the client:
  ```bash
  python3 c2_client/client.py --name <unique-device-name>
  ```
- The device will now appear in the GUI control panel on your server machine.

## Technology Stack

- **Backend:** FastAPI, Uvicorn, SQLAlchemy
- **GUI:** CustomTkinter
- **Database:** SQLite
- **Client:** Python standard libraries, Requests

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
