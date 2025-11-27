import multiprocessing
import uvicorn
import time
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# --- Path Fix ---
# Get the absolute path of the project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# Add the project root to the Python path
sys.path.insert(0, PROJECT_ROOT)

from c2_server.main import app as fastapi_app
from gui.main_app import App

def run_server(project_path):
    """Runs the FastAPI server and redirects its logs to a file."""
    # Add the project path to the new process's sys.path as well
    sys.path.insert(0, project_path)

    log_file_path = os.path.join(PROJECT_ROOT, "server_debug.log")
    
    # Configure basic logging to file for the root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                log_file_path,
                maxBytes=10 * 1024 * 1024, # 10 MB
                backupCount=5
            )
        ]
    )

    uvicorn.run("c2_server.main:app", host="0.0.0.0", port=8000, log_level="debug")

if __name__ == "__main__":
    # Set start method for multiprocessing (important for PyInstaller)
    multiprocessing.set_start_method('spawn', force=True)

    # Start the FastAPI server in a separate, daemonic process
    print("Starting backend server (logs to server_debug.log)...")
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
