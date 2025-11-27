# Raspyjack C2 - Command & Control Center
![image](https://github.com/user-attachments/assets/a0292a5b-6f37-4a42-abcc-c0a978f1ce6c)

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
       |       polls for commands, sends results                     | issues commands,
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

**Important Database Note (`c2.db`):**
The C2 server uses an SQLite database file named `c2.db` (located in the `RaspyjackC2` project root) to store all device registrations, tasks, and results.

*   **Deleting `c2.db`:** If you delete this file, all registered devices and their associated data will be lost. The server will automatically recreate an empty `c2.db` with fresh tables upon its next startup.
*   **Device Re-registration:** If `c2.db` is deleted or replaced, any previously registered clients will no longer be recognized by the server. You will need to force these clients to re-register. To do this, delete the `device_config.json` file on the client device (e.g., `/root/Raspyjack/device_config.json`) and then restart the client. The client will then automatically register as a new device.

**Debugging Server Issues:**
If you encounter server-side errors (e.g., `500 Internal Server Error` during client registration), it's often helpful to run the server in the foreground to see detailed error messages.

1.  **Stop any running background server process:**
    ```bash
    # Find the PID of the uvicorn/python3 process listening on port 8000
    lsof -i :8000
    # Kill the process (replace <PID> with the actual PID)
    kill <PID>
    ```
2.  **Start the application in the foreground:**
    ```bash
    python raspyC2.py
    ```
    This will display all server logs and errors directly in your terminal. Once debugging is complete, you can stop it with `Ctrl+C` and restart it in the background if desired.

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
    sudo python3 c2_client/client.py install --c2-url https://<your-server-ip>:8000
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
  python3 c2_client/client.py --name <unique-device-name> --c2-url https://<your-server-ip>:8000
  ```
  Replace `<unique-device-name>` with a name for your device and `<your-server-ip>` with the local IP address of the computer running the C2 server.
  The device will now appear in the GUI control panel on your server machine.

## Secure Internet Deployment

To securely operate Raspyjack C2 over the internet, follow these critical steps:

### 1. HTTPS Configuration (Server)

The C2 server now uses HTTPS for encrypted communication.

*   **Generate SSL Certificates:**
    *   **For Development/Testing (Self-Signed):** You can generate self-signed certificates using `openssl`. Place `cert.pem` and `key.pem` in the `c2_server/` directory.
        ```bash
        openssl req -x509 -newkey rsa:4096 -nodes -out c2_server/cert.pem -keyout c2_server/key.pem -days 365
        ```
        *   **For Production (CA-Signed):** Obtain certificates from a trusted Certificate Authority (CA) like Let's Encrypt. Configure your domain and web server (e.g., Nginx, Apache) to handle SSL termination and proxy requests to the FastAPI application.
*   **Uvicorn Configuration:** The `raspyC2.py` script automatically configures Uvicorn to use `c2_server/cert.pem` and `c2_server/key.pem`.

### 2. API Key Authentication

Clients now authenticate using a unique API key.

*   **Registration:** When a client registers, the server generates and returns a unique API key. This key is stored in `device_config.json` on the client.
*   **Client Requests:** The client includes this API key in the `X-API-Key` header for all subsequent requests.
*   **Server Validation:** The server validates this API key against its database to authenticate the client.

### 3. Client Configuration

*   **HTTPS URL:** Ensure the `--c2-url` argument for the client uses `https://` (e.g., `https://<your-server-ip>:8000`).
*   **SSL Verification (Development Warning):** For development with self-signed certificates, the client (and GUI) are configured with `verify=False` to bypass SSL certificate validation. **This is INSECURE and MUST be changed to `verify=True` in a production environment with proper CA-signed certificates.**

### 4. GUI Considerations

*   The GUI also connects to the server via `https://`.
*   Similar to the client, the GUI uses `verify=False` for development. **Change this to `verify=True` in production.**
*   **GUI Authentication (Future Work):** Currently, the GUI does not implement its own authentication mechanism to the C2 server. It assumes it's running on a trusted machine. For multi-user or highly sensitive deployments, implementing GUI user authentication (e.g., username/password, separate API key for GUI) would be necessary.

### 5. Network Accessibility (Firewall & Port Forwarding)

*   **Public IP/Domain:** Your C2 server needs a public IP address or a domain name that resolves to it.
*   **Port Forwarding:** Configure your router/firewall to forward incoming HTTPS traffic (typically port 443, or 8000 if directly exposing Uvicorn) to the machine running the C2 server.
*   **Firewall Rules:** Ensure your server's operating system firewall (e.g., `ufw`, `firewalld`) allows incoming connections on the chosen HTTPS port.

### 6. Using Ngrok for Development/Testing

For quickly exposing your local C2 server to the internet during development or testing, `ngrok` (or similar tunneling services) can be very useful.

*   **Install Ngrok:** Follow the official `ngrok` installation guide for your operating system.
*   **Start your local C2 Server:** Run `python raspyC2.py` as usual. This will start the FastAPI backend on `https://127.0.0.1:8000`.
*   **Start Ngrok Tunnel:** Open a new terminal and run `ngrok http https://localhost:8000`.
    *   `ngrok` will provide a public HTTPS URL (e.g., `https://xxxx-xxxx-xxxx-xxxx.ngrok-free.app`).
    *   This command tells `ngrok` to tunnel incoming HTTPS requests from its public endpoint to your local HTTPS server running on port 8000.
*   **Update Client `C2_URL`:** Use the `ngrok` provided public URL when installing or running your client:
    ```bash
    sudo python3 c2_client/client.py install --c2-url https://xxxx-xxxx-xxxx-xxxx.ngrok-free.app
    ```
    Replace `https://xxxx-xxxx-xxxx-xxxx.ngrok-free.app` with your actual `ngrok` URL.
*   **Security Note:** While `ngrok` provides HTTPS for the public endpoint, the generated URL is publicly accessible. Always ensure your API key authentication is robust. This method is primarily for convenience in development and testing, not for production deployments.

## Technology Stack

- **Backend:** FastAPI, Uvicorn, SQLAlchemy
- **GUI:** CustomTkinter
- **Database:** SQLite
- **Client:** Python standard libraries, Requests

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
