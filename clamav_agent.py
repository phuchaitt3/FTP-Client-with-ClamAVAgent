import socket
import subprocess
import os
import logging

# --- Configuration ---
HOST = '127.0.0.1'  # Localhost
PORT = 6789         # Port to listen on
TEMP_DIR = "temp_scans"
LOG_FILE = "clamav_agent.log"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def setup_environment():
    """Create the temporary directory for file scans if it doesn't exist."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        logging.info(f"Created temporary scan directory: {TEMP_DIR}")

import subprocess
import os
import logging

def scan_file(file_path):
    """
    Scans a file using the real clamscan command and checks its exit code.
    """
    # Ensure the file exists before scanning
    if not os.path.exists(file_path):
        logging.error(f"File does not exist at path: {file_path}")
        return "ERROR: File not found for scanning"

    logging.info(f"Running clamscan on: {file_path}")
    
    try:
        # Use subprocess.run to execute the command.
        # We check the return code to determine the result.
        # The 'capture_output=True' and 'text=True' arguments are helpful for logging.
        # We don't use 'check=True' here because we want to handle non-zero exit codes ourselves.
        result = subprocess.run(
            ['clamscan', '--no-summary', file_path],
            capture_output=True,
            text=True
        )

        # Check the return code from clamscan
        if result.returncode == 0:
            logging.info(f"Scan result for {file_path}: OK")
            return "OK"
        elif result.returncode == 1:
            logging.warning(f"Scan result for {file_path}: INFECTED\n{result.stdout.strip()}")
            return "INFECTED"
        else: # Any other non-zero return code is an error
            logging.error(f"Clamscan failed with error code {result.returncode} for file {file_path}.")
            logging.error(f"Clamscan stderr: {result.stderr.strip()}")
            return f"ERROR: Scan failed"
            
    except FileNotFoundError:
        logging.error("`clamscan` command not found. Please ensure ClamAV is installed and in your system's PATH.")
        return "ERROR: clamscan not found"
    except Exception as e:
        logging.error(f"An unexpected error occurred during scan: {e}")
        return f"ERROR: {e}"


def handle_client(conn, addr):
    """Handle a single client connection."""
    logging.info(f"Accepted connection from {addr}")
    try:
        # 1. Receive file metadata (filename and size)
        # Protocol: "filename.ext:filesize"
        metadata = conn.recv(1024).decode()
        filename, filesize_str = metadata.split(':')
        filesize = int(filesize_str)
        
        logging.info(f"Receiving file '{filename}' ({filesize} bytes) from {addr}")
        
        # Send acknowledgment to start file transfer
        conn.sendall(b"META_OK")
        
        # 2. Receive file data
        temp_file_path = os.path.join(TEMP_DIR, os.path.basename(filename))
        with open(temp_file_path, 'wb') as f:
            received_bytes = 0
            while received_bytes < filesize:
                data = conn.recv(4096)
                if not data:
                    break
                f.write(data)
                received_bytes += len(data)

        if received_bytes == filesize:
            logging.info(f"File '{filename}' received successfully.")
            # 3. Scan the file
            print(f"Scanning file: {temp_file_path}")
            scan_result = scan_file(temp_file_path)
            
            # 4. Send result back to client
            conn.sendall(scan_result.encode())
            logging.info(f"Sent result '{scan_result}' to {addr}")
        else:
            logging.error(f"File transfer incomplete for '{filename}'. Expected {filesize}, got {received_bytes}")
            conn.sendall(b"ERROR: Incomplete file transfer")

    except Exception as e:
        logging.error(f"An error occurred with client {addr}: {e}")
    finally:
        # 5. Cleanup
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logging.info(f"Cleaned up temporary file: {temp_file_path}")
        conn.close()
        logging.info(f"Connection with {addr} closed.")


def main():
    """Main function to run the ClamAV agent server."""
    setup_environment()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        logging.info(f"ClamAV Agent listening on {HOST}:{PORT}")
        
        while True:
            try:
                conn, addr = s.accept()
                # In a real-world server, you would use threading or asyncio
                # to handle multiple clients concurrently.
                handle_client(conn, addr)
            except KeyboardInterrupt:
                logging.info("Server is shutting down.")
                break
            except Exception as e:
                logging.error(f"Main loop error: {e}")

if __name__ == "__main__":
    main()
