import multiprocessing
import uvicorn
import time
import sys
import os

# --- Path Fix ---
# Get the absolute path of the project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# Add the project root to the Python path
sys.path.insert(0, PROJECT_ROOT)

from c2_server.main import app as fastapi_app
from gui.main_app import App

def run_server(project_path):
    """Runs the FastAPI server in a quiet mode."""
    # Add the project path to the new process's sys.path as well
    sys.path.insert(0, project_path)
    uvicorn.run(
        "c2_server.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        ssl_keyfile=os.path.join(project_path, "c2_server", "key.pem"),
        ssl_certfile=os.path.join(project_path, "c2_server", "cert.pem")
    )

if __name__ == "__main__":
    # Set start method for multiprocessing (important for PyInstaller)
    multiprocessing.set_start_method('spawn', force=True)

    # Start the FastAPI server in a separate, daemonic process
    print("Starting backend server...")
    server_process = multiprocessing.Process(target=run_server, args=(PROJECT_ROOT,))
    server_process.daemon = True
    server_process.start()
    
    # Give the server a moment to start up before launching the GUI
    time.sleep(3)
    print("Launching GUI...")

    # Create the GUI App instance
    app = App()

    def on_closing():
        """Function to be called when the main window is closed."""
        print("GUI closed, explicitly terminating server process...")
        server_process.terminate()
        server_process.join() # Wait for the process to terminate
        print("Server process terminated.")
        app.destroy()

    # Bind the closing function to the window's close button
    app.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Run the GUI main loop
    app.mainloop()
