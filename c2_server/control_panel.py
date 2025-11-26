from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable
from textual.timer import Timer

import requests

C2_API_URL = "http://127.0.0.1:8000/api"

class ControlPanelApp(App):
    """A Textual app to control the Raspyjack C2."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]
    
    TITLE = "Raspyjack C2 Control Panel"
    SUB_TITLE = "The TUI is a work in progress."

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield DataTable(id="devices_table")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.update_devices_table_timer = self.set_interval(5, self.update_devices_table)
        self.update_devices_table()

    def update_devices_table(self) -> None:
        """Fetches device data and updates the table."""
        table = self.query_one(DataTable)
        
        # Add columns on first update
        if not table.columns:
            table.add_columns("ID", "Name", "IP Address", "Last Seen")

        try:
            response = requests.get(f"{C2_API_URL}/devices")
            response.raise_for_status()
            devices = response.json()
            
            table.clear()
            for device in devices:
                table.add_row(
                    device.get("id"),
                    device.get("name"),
                    device.get("ip_address"),
                    device.get("last_seen"),
                )
        except requests.RequestException as e:
            self.sub_title = f"Error fetching devices: {e}"


    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

if __name__ == "__main__":
    app = ControlPanelApp()
    app.run()
