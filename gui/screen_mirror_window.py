import customtkinter
import requests
from PIL import Image
import io

C2_API_URL = "https://127.0.0.1:8000/api"

class ScreenMirrorWindow(customtkinter.CTkToplevel):
    def __init__(self, master, device_id):
        super().__init__(master)
        self.device_id = device_id
        self.master_app = master

        self.title(f"Screen Mirror - {device_id[:8]}...")
        self.geometry("400x400")

        self.image_label = customtkinter.CTkLabel(self, text="Waiting for stream...")
        self.image_label.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(1000, self.fetch_frame)

    def fetch_frame(self):
        try:
            response = requests.get(f"{C2_API_URL}/screen/{self.device_id}", timeout=2, verify=False)
            if response.status_code == 200:
                pil_image = Image.open(io.BytesIO(response.content))
                ctk_image = customtkinter.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)
                self.image_label.configure(image=ctk_image, text="")
            else:
                self.image_label.configure(text=f"No Stream (Status: {response.status_code})")
        except requests.RequestException:
            self.image_label.configure(text="Connection Error")
        
        # Continue polling even if there was an error
        self.after(1000, self.fetch_frame)

    def on_close(self):
        print("Closing screen mirror, stopping stream...")
        self.master_app.send_command_internal("c2_screencap_stop")
        self.destroy()
