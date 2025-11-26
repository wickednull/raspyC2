import requests
import json
import argparse
import os
import time
import subprocess

C2_URL = "http://127.0.0.1:8000/api"
CONFIG_FILE = "device_config.json"

def get_device_config(name: str):
    """
    Loads device config from file, or registers the device if not found.
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        print(f"Device config loaded. ID: {config.get('id')}")
        return config

    print(f"No config found. Attempting to register device with name: {name}")
    try:
        payload = {"name": name}
        response = requests.post(f"{C2_URL}/register", json=payload)
        response.raise_for_status()

        config = response.json()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"Device registered successfully! ID: {config.get('id')}")
        return config

    except requests.exceptions.RequestException as e:
        print(f"Fatal error during registration: {e}")
        return None

def fetch_commands(device_id: str):
    """Polls the C2 server for new commands."""
    try:
        response = requests.get(f"{C2_URL}/commands/{device_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching commands: {e}")
        return []

def execute_command(command: str):
    """Executes a command and returns the output."""
    print(f"Executing command: '{command}'")
    try:
        # Using shell=True for simplicity, but be aware of security implications
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Execution failed: {str(e)}"

def submit_result(device_id: str, task_id: int, output: str):
    """Sends the result of a command back to the C2 server."""
    try:
        payload = {"task_id": task_id, "output": output}
        response = requests.post(f"{C2_URL}/results/{device_id}", json=payload)
        response.raise_for_status()
        print(f"Result for task {task_id} submitted successfully.")
    except requests.RequestException as e:
        print(f"Error submitting result: {e}")

def main_loop(device_config):
    """The main polling loop for the client."""
    device_id = device_config.get("id")
    if not device_id:
        print("Fatal: Device ID not found in config.")
        return

    print(f"Starting C2 client for device {device_id}. Polling for commands...")
    while True:
        tasks = fetch_commands(device_id)
        if tasks:
            print(f"Received {len(tasks)} new task(s).")
            for task in tasks:
                task_id = task.get("id")
                command = task.get("command")
                
                output = execute_command(command)
                submit_result(device_id, task_id, output)
        
        time.sleep(10) # Poll every 10 seconds

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raspyjack C2 Client")
    parser.add_argument("--name", default="raspy-01", help="A unique name for this device")
    args = parser.parse_args()

    config = get_device_config(args.name)
    if config:
        main_loop(config)
    else:
        print("Could not start client.")