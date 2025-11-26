import customtkinter
import requests
from functools import partial
import os
import json
from gui.screen_mirror_window import ScreenMirrorWindow

C2_API_URL = "http://127.0.0.1:8000/api"
DEBUG_API_URL = "http://127.0.0.1:8000/debug"

PAYLOADS = [
    {"name": "Deauth Scan", "script": "deauth.py", "description": "Scans for networks and performs a deauthentication attack."},
    {"name": "Snake Game", "script": "snake.py", "description": "Launches a simple snake game on the device's LCD."},
    {"name": "Auto Nmap Scan", "script": "autoNmapScan.py", "description": "Performs an automated Nmap scan of the local network."},
    {"name": "WiFi Manager", "script": "wifi_manager_payload.py", "description": "Starts a simple WiFi manager on the device."}
]

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Raspyjack C2 Control Panel")
        self.geometry("1024x768")
        self.selected_device_id = None
        self.selected_device_button = None
        self.device_widgets = {}
        self.screen_mirror_window = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Left Frame ---
        self.device_list_frame = customtkinter.CTkScrollableFrame(self, label_text="Devices")
        self.device_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")
        self.refresh_button = customtkinter.CTkButton(self.device_list_frame, text="Refresh", command=self.refresh_devices)
        self.refresh_button.pack(fill="x", padx=5, pady=5)
        self.screen_mirror_button = customtkinter.CTkButton(self.device_list_frame, text="Start Screen Mirror", command=self.open_screen_mirror, state="disabled")
        self.screen_mirror_button.pack(fill="x", padx=5, pady=5)
        self.delete_device_button = customtkinter.CTkButton(self.device_list_frame, text="Delete Selected Device", command=self.confirm_delete_device, state="disabled", fg_color="#D32F2F")
        self.delete_device_button.pack(fill="x", padx=5, pady=(20,5))

        # --- Right Frame (Tabbed View) ---
        self.tab_view = customtkinter.CTkTabview(self)
        self.tab_view.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("Shell")
        self.tab_view.add("File Manager")
        self.tab_view.add("Payloads")
        self.tab_view.add("Device Details")
        self.tab_view.add("Debug")

        self.setup_tabs()

        self.after(100, self.refresh_devices)
        self.after(5000, self.auto_refresh)

    def setup_tabs(self):
        # This function just groups the tab setup code
        # -- Shell Tab --
        self.tab_view.tab("Shell").grid_rowconfigure(0, weight=1)
        self.tab_view.tab("Shell").grid_columnconfigure(0, weight=1)
        self.results_box = customtkinter.CTkTextbox(self.tab_view.tab("Shell"), state="disabled")
        self.results_box.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.command_frame = customtkinter.CTkFrame(self.tab_view.tab("Shell"))
        self.command_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.command_frame.grid_columnconfigure(0, weight=1)
        self.command_entry = customtkinter.CTkEntry(self.command_frame, placeholder_text="Enter command...")
        self.command_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.send_button = customtkinter.CTkButton(self.command_frame, text="Send Command", command=self.send_command_from_entry)
        self.send_button.grid(row=0, column=1, padx=5, pady=5)

        # -- File Manager Tab --
        self.tab_view.tab("File Manager").grid_columnconfigure(0, weight=1)
        self.fm_controls_frame = customtkinter.CTkFrame(self.tab_view.tab("File Manager"))
        self.fm_controls_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.fm_controls_frame.grid_columnconfigure(1, weight=1)
        self.fm_up_button = customtkinter.CTkButton(self.fm_controls_frame, text="Up", width=50, command=self.fm_up)
        self.fm_up_button.grid(row=0, column=0, padx=5, pady=5)
        self.fm_path_entry = customtkinter.CTkEntry(self.fm_controls_frame, placeholder_text="Current Path")
        self.fm_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.fm_go_button = customtkinter.CTkButton(self.fm_controls_frame, text="Go", width=50, command=self.fm_go)
        self.fm_go_button.grid(row=0, column=2, padx=5, pady=5)
        self.fm_output_label = customtkinter.CTkLabel(self.tab_view.tab("File Manager"), text="File Manager output will appear in the 'Shell' tab's results box.", anchor="w")
        self.fm_output_label.grid(row=1, column=0, padx=10, pady=10, sticky="new")

        # -- Payloads Tab --
        self.payload_scroll_frame = customtkinter.CTkScrollableFrame(self.tab_view.tab("Payloads"), label_text="One-Click Payloads")
        self.payload_scroll_frame.pack(in_=self.tab_view.tab("Payloads"), fill="both", expand=True, padx=5, pady=5)
        self.populate_payloads()

        # -- Device Details Tab --
        self.details_button = customtkinter.CTkButton(self.tab_view.tab("Device Details"), text="Fetch Device Details", command=self.fetch_details)
        self.details_button.pack(in_=self.tab_view.tab("Device Details"), padx=20, pady=20)
        self.details_label = customtkinter.CTkLabel(self.tab_view.tab("Device Details"), text="Device details will be fetched and displayed in the 'Shell' tab.", anchor="w")
        self.details_label.pack(in_=self.tab_view.tab("Device Details"), padx=20, pady=10, fill="x")

        # -- Debug Tab --
        self.debug_frame = customtkinter.CTkFrame(self.tab_view.tab("Debug"))
        self.debug_frame.pack(in_=self.tab_view.tab("Debug"), padx=20, pady=20, fill="x")
        self.debug_tasks_button = customtkinter.CTkButton(self.debug_frame, text="Dump All Tasks", command=lambda: self.debug_dump("tasks"))
        self.debug_tasks_button.pack(side="left", expand=True, padx=10, pady=10)
        self.debug_results_button = customtkinter.CTkButton(self.debug_frame, text="Dump All Results", command=lambda: self.debug_dump("results"))
        self.debug_results_button.pack(side="left", expand=True, padx=10, pady=10)

    def confirm_delete_device(self):
        if not self.selected_device_id:
            return

        dialog = customtkinter.CTkToplevel(self)
        dialog.title("Confirm Deletion")
        dialog.geometry("350x150")
        dialog.transient(self)
        
        def on_yes():
            self.delete_device()
            dialog.destroy()

        message = f"Are you sure you want to delete device {self.selected_device_id[:8]}... and all its data?"
        label = customtkinter.CTkLabel(dialog, text=message, wraplength=300)
        label.pack(padx=20, pady=20)

        button_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        yes_button = customtkinter.CTkButton(button_frame, text="Yes", command=on_yes, fg_color="red")
        yes_button.pack(side="left", padx=10)

        no_button = customtkinter.CTkButton(button_frame, text="No", command=dialog.destroy)
        no_button.pack(side="left", padx=10)
        
        # Delay grab_set to prevent TclError
        dialog.after(100, dialog.grab_set)
        
        self.wait_window(dialog)

    def delete_device(self):
        if not self.selected_device_id: return
        try:
            print(f"Attempting to delete device {self.selected_device_id}...")
            response = requests.delete(f"{C2_API_URL}/devices/{self.selected_device_id}")
            response.raise_for_status()
            print(f"Device {self.selected_device_id} deleted successfully.")
            self.selected_device_id = None
            self.selected_device_button = None
            self.delete_device_button.configure(state="disabled")
            self.screen_mirror_button.configure(state="disabled")
            self.refresh_devices()
        except requests.RequestException as e:
            print(f"Error deleting device: {e}")

    def debug_dump(self, dump_type: str):
        try:
            response = requests.get(f"{DEBUG_API_URL}/{dump_type}")
            response.raise_for_status()
            data = response.json()
            output = f"--- DEBUG DUMP: {dump_type.upper()} ---\n\n"
            output += json.dumps(data, indent=2)
            self.results_box.configure(state="normal")
            self.results_box.delete("1.0", "end")
            self.results_box.insert("1.0", output)
            self.results_box.configure(state="disabled")
            self.tab_view.set("Shell")
        except requests.RequestException as e:
            print(f"Error during debug dump: {e}")

    def fetch_details(self):
        self.send_command_internal("c2_get_details")
        self.tab_view.set("Shell")

    def populate_payloads(self):
        for payload in PAYLOADS:
            frame = customtkinter.CTkFrame(self.payload_scroll_frame)
            frame.pack(fill="x", padx=10, pady=5)
            frame.grid_columnconfigure(0, weight=1)
            label = customtkinter.CTkLabel(frame, text=f"{payload['name']}\n{payload['description']}", anchor="w", justify="left")
            label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
            button = customtkinter.CTkButton(frame, text="Launch", width=100, command=partial(self.run_payload, payload['script']))
            button.grid(row=0, column=1, padx=10, pady=10)

    def run_payload(self, script_name):
        command = f"python3 payloads/{script_name}"
        self.send_command_internal(command)
        self.tab_view.set("Shell")

    def fm_go(self):
        path = self.fm_path_entry.get() or "."
        self.send_command_internal(f"c2_ls {path}")
        self.tab_view.set("Shell")

    def fm_up(self):
        parent_path = os.path.dirname(self.fm_path_entry.get() or ".")
        self.fm_path_entry.delete(0, "end")
        self.fm_path_entry.insert(0, parent_path)
        self.fm_go()

    def auto_refresh(self):
        self.refresh_devices()
        self.refresh_results()
        self.after(5000, self.auto_refresh)

    def select_device(self, device_id, button):
        if self.selected_device_button:
            self.selected_device_button.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])
        self.selected_device_id = device_id
        self.selected_device_button = button
        button.configure(fg_color="green")
        self.screen_mirror_button.configure(state="normal")
        self.delete_device_button.configure(state="normal")
        self.fm_path_entry.delete(0, "end")
        self.fm_path_entry.insert(0, ".")
        self.refresh_results()

    def open_screen_mirror(self):
        if not self.selected_device_id: return
        if self.screen_mirror_window is None or not self.screen_mirror_window.winfo_exists():
            self.send_command_internal("c2_screencap_start")
            self.screen_mirror_window = ScreenMirrorWindow(self, self.selected_device_id)
        else: self.screen_mirror_window.focus()

    def refresh_devices(self):
        try:
            response = requests.get(f"{C2_API_URL}/devices")
            response.raise_for_status()
            devices = response.json()
            current_ids = {d['id'] for d in devices}
            for device_id, widget in list(self.device_widgets.items()):
                if device_id not in current_ids:
                    widget.destroy()
                    del self.device_widgets[device_id]
            for device in devices:
                if device['id'] not in self.device_widgets:
                    name, device_id = device.get("name"), device.get("id")
                    button = customtkinter.CTkButton(self.device_list_frame, text=f"{name} ({device_id[:8]}...)")
                    button.configure(command=partial(self.select_device, device_id, button))
                    button.pack(fill="x", padx=5, pady=5)
                    self.device_widgets[device_id] = button
        except requests.RequestException as e:
            print(f"Error fetching devices: {e}")
            pass

    def refresh_results(self):
        if not self.selected_device_id: return
        try:
            response = requests.get(f"{C2_API_URL}/results/{self.selected_device_id}")
            response.raise_for_status()
            results = response.json()
            self.results_box.configure(state="normal")
            self.results_box.delete("1.0", "end")
            log_content = f"--- Results for {self.selected_device_id[:8]}... ---\n\n"
            for res in results:
                log_content += f"[{res['created_at']}] Task {res['task_id']}:\n{res['output']}\n---------------------------------"
            self.results_box.insert("1.0", log_content)
            self.results_box.configure(state="disabled")
        except requests.RequestException as e:
            print(f"Error fetching results: {e}")
            self.results_box.configure(state="normal")
            self.results_box.delete("1.0", "end")
            self.results_box.insert("1.0", "Could not fetch results.")
            self.results_box.configure(state="disabled")

    def send_command_internal(self, command):
        if not self.selected_device_id:
            print("Error: No device selected.")
            return
        try:
            payload = {"device_id": self.selected_device_id, "command": command}
            response = requests.post(f"{C2_API_URL}/tasks", json=payload)
            response.raise_for_status()
            print(f"Internal command '{command}' sent to {self.selected_device_id[:8]}...")
        except requests.RequestException as e:
            print(f"Error sending internal command: {e}")

    def send_command_from_entry(self):
        command = self.command_entry.get()
        if not command: return
        self.send_command_internal(command)
        self.command_entry.delete(0, "end")