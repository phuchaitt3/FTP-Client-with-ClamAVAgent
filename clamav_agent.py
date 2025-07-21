# clamav_agent.py
import socket
import subprocess
import os

# --- Configuration ---
# HOST = '127.0.0.1'  # Localhost
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 6789         # Port to listen on
TEMP_DIR = "temp_scans"

def setup_environment():
    """Create the temporary directory for file scans if it doesn't exist."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        print(f"Created temporary scan directory: {TEMP_DIR}")

def scan_file(file_path):
    """
    Scans a file using the real clamscan command and checks its exit code.
    """
    # Ensure the file exists before scanning
    if not os.path.exists(file_path):
        print(f"ERROR: File does not exist at path: {file_path}")
        return "ERROR: File not found for scanning"

    try:
        # Use subprocess.run to execute the command.
        # We check the return code to determine the result.
        result = subprocess.run(
            ['clamscan', '--no-summary', file_path],
            capture_output=True,
            text=True
        )

        # Check the return code from clamscan
        if result.returncode == 0:
            return "OK"
        elif result.returncode == 1:
            # An infected file is a result, not an error in the program's execution
            return "INFECTED"
        else: # Any other non-zero return code is an error
            print(f"ERROR: Clamscan failed with error code {result.returncode} for file {file_path}.")
            print(f"ERROR: Clamscan stderr: {result.stderr.strip()}")
            return "ERROR: Scan failed"

    except FileNotFoundError:
        print("ERROR: `clamscan` command not found. Please ensure ClamAV is installed and in your system's PATH.")
        return "ERROR: clamscan not found"
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during scan: {e}")
        return f"ERROR: {e}"

def handle_client(conn, addr):
    """Handle a single client connection."""
    try:
        # 1. Receive file metadata (filename and size)
        metadata = conn.recv(1024).decode()
        if not metadata:
            print(f"ERROR: Client {addr} connected but sent no data.")
            return

        filename, filesize_str = metadata.split(':')
        filesize = int(filesize_str)

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
            # 3. Scan the file
            scan_result = scan_file(temp_file_path)

            # 4. Send result back to client
            conn.sendall(scan_result.encode())
        else:
            print(f"ERROR: File transfer incomplete for '{filename}'. Expected {filesize}, got {received_bytes}")
            conn.sendall(b"ERROR: Incomplete file transfer")

    except Exception as e:
        print(f"ERROR: An error occurred with client {addr}: {e}")
    finally:
        # 5. Cleanup
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        conn.close()

def main():
    """Main function to run the ClamAV agent server."""
    setup_environment()
    print(f"ClamAV Agent listening on {HOST}:{PORT}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()

        while True:
            try:
                conn, addr = s.accept()
                # In a real-world server, you would use threading or asyncio
                # to handle multiple clients concurrently.
                handle_client(conn, addr)
            except KeyboardInterrupt:
                print("\nServer is shutting down.")
                break
            except Exception as e:
                print(f"ERROR: Main loop error: {e}")

if __name__ == "__main__":
    main()