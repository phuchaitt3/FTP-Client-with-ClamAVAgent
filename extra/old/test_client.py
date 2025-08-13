# test_client.py

import socket
import os
import sys

# --- Configuration ---
AGENT_HOST = '127.0.0.1'
AGENT_PORT = 6789

def send_file_to_agent(filepath):
    """Connects to the agent, sends a file, and prints the response."""
    if not os.path.exists(filepath):
        print(f"Error: File not found at '{filepath}'")
        return

    try:
        # Create a socket and connect to the agent
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"Connecting to ClamAV agent at {AGENT_HOST}:{AGENT_PORT}...")
            s.connect((AGENT_HOST, AGENT_PORT))
            print("Connected.")

            # Prepare metadata (filename:filesize)
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            metadata = f"{filename}:{filesize}".encode()

            # 1. Send metadata
            print(f"Sending metadata: {metadata.decode()}")
            s.sendall(metadata)

            # 2. Wait for agent's confirmation
            response = s.recv(1024)
            if response != b"META_OK":
                print(f"Agent did not acknowledge metadata. Response: {response.decode()}")
                return

            # 3. Send the file data
            print("Sending file data...")
            with open(filepath, 'rb') as f:
                s.sendall(f.read())
            print("File sent.")

            # 4. Receive the scan result
            scan_result = s.recv(1024).decode()
            print("\n--- SCAN RESULT ---")
            print(f"File '{filename}' was scanned. Result: {scan_result}")
            print("---------------------\n")

    except ConnectionRefusedError:
        print("Connection failed. Is the clamav_agent.py script running?")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_client.py <path_to_file>")
        sys.exit(1)
    
    file_to_send = sys.argv[1]
    send_file_to_agent(file_to_send)