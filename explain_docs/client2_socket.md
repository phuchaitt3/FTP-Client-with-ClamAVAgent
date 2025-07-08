Yes, there is socket code in `client2.py`.

Specifically, the `scan_with_clamav` method uses the `socket` module to communicate with the ClamAV agent:

```python
    def scan_with_clamav(self, filepath):
        try:
            filesize = os.path.getsize(filepath)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # <--- Socket creation
            s.connect((CLAMAV_HOST, CLAMAV_PORT))                 # <--- Connect to the agent

            metadata = f"{os.path.basename(filepath)}:{filesize}"
            s.sendall(metadata.encode())                          # <--- Sending data over socket
            ack = s.recv(1024)                                    # <--- Receiving data from socket
            if ack != b"META_OK":
                s.close()
                return "ERROR: ClamAVAgent did not acknowledge metadata."

            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    s.sendall(data)                               # <--- Sending file data over socket

            result = s.recv(1024).decode()                        # <--- Receiving scan result
            s.close()                                             # <--- Closing the socket
            return result
        except Exception as e:
            return f"ERROR: {str(e)}"
```

This method creates a TCP/IP socket (`socket.AF_INET`, `socket.SOCK_STREAM`), connects it to the defined `CLAMAV_HOST` and `CLAMAV_PORT`, sends file metadata and the file content, and then receives the scan result.