# ftp_client.py
import os
import socket
import fnmatch
# import glob
import re
import configparser
import sys
import time       # Ensure time is imported
import threading  # The key module for this solution
import logging

BUFFER_SIZE = 4096 # 4KB

# --- Setup for Debug Logging to a File (place this at the top of your file, once) ---
# Create a logger specific for debug messages
debug_logger = logging.getLogger('ftp_client.debug')
debug_logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG

# Create a file handler for debug messages.
# mode='w' will create a new empty file each time the script is run.
# If you wanted to keep adding to the same file, you would use mode='a' (for append).
debug_handler = logging.FileHandler('debug.log', mode='w')
debug_handler.setLevel(logging.DEBUG) # Ensure this handler processes DEBUG level messages

# Define the format for your debug messages, including a timestamp
formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s: %(message)s')
debug_handler.setFormatter(formatter)

# Add the handler to the logger, but only if it doesn't already have one
if not debug_logger.handlers:
    debug_logger.addHandler(debug_handler)

# Prevent messages from being propagated to the root logger
debug_logger.propagate = False
# --- End of Setup ---

class RawFTPClient:
    def __init__(self):
        """Initializes the FTP client instance with default settings.

        Attributes:
            control_sock (socket.socket|None): The control connection socket to the FTP server.
            passive_mode (bool): True if passive mode is enabled, False for active mode.
            active_data_listener (socket.socket|None): Listening socket for active mode.
            local_test_mode (bool): If True, active mode will bind to 127.0.0.1 for local testing.
            transfer_mode (str): File transfer type, either 'binary' or 'ascii'.
            prompt (bool): If True, prompt user before each transfer in mget/mput.
            connected (bool): Connection status to the server.
            host (str|None): The connected FTP server's hostname or IP.
            clamav_host (str|None): Host for ClamAV scanning agent.
            clamav_port (int|None): Port for ClamAV scanning agent.
        """
        # --- FTP Control Connection Attributes ---
        self.control_sock = None  # Socket object for the main control connection (commands & responses)
                                  # It will be set when connected to an FTP server.
        
        # --- FTP Transfer Attributes ---
        self.passive_mode = True  # Boolean flag: True for Passive Mode (client connects to server's data port),
                                  # False for Active Mode (server connects to client's data port).
                                  # Passive mode is generally preferred due to firewall/NAT compatibility.
        self.active_data_listener = None # Socket object for the data connection listener in Active Mode.
                                          # This socket waits for the FTP server to connect to the client.
        self.local_test_mode = False  # Boolean flag: If True, forces Active Mode to use 127.0.0.1 (loopback)
                                      # for its IP address in the PORT command. Useful for local testing
                                      # without NAT/firewall issues. Defaults to False (uses real IP).
        
        self.transfer_mode = 'binary' # String: 'binary' (TYPE I) for all file types,
                                      # 'ascii' (TYPE A) for text files (handles line endings).
        self.prompt = True            # Boolean flag: If True, mput/mget commands will prompt for confirmation
                                      # before transferring each file.
        self.connected = False        # Boolean flag: True if currently connected and logged into an FTP server,
                                      # False otherwise.

        # --- Connection Details ---
        self.host = None              # String: IP address of the currently connected FTP server.
        self.clamav_host = None       # String: IP address of the ClamAV scanning agent.
                                      # Loaded from config.ini.
        self.clamav_port = None       # Integer: The port number of the ClamAV scanning agent.
                                      # Loaded from config.ini.

    def _spinner_animation(self, stop_event):
        """
        Displays a spinning character in the console.
        This function is meant to be run in a separate thread.
        """
        spinner_chars = ['|', '/', '-', '\\']
        i = 0
        while not stop_event.is_set():
            char = spinner_chars[i % len(spinner_chars)]
            # Use carriage return '\r' to move the cursor to the beginning of the line
            sys.stdout.write(char + '\b')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        # Clear the spinner character when done
        sys.stdout.write(' \b')
        sys.stdout.flush()

    # Method to load the configuration
    def load_config(self):
        """Loads configuration from config.ini file."""
        config = configparser.ConfigParser()
        # Get the absolute path to the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Join the script's directory with the config file name
        config_path = os.path.join(script_dir, 'config.ini')
        try:
            # The config.read() method can directly take the path
            if not config.read(config_path):
                # config.read() returns an empty list if the file is not found or is empty
                raise FileNotFoundError
            
            self.clamav_host = config['DEFAULT'].get('clamav_host')
            self.clamav_port = config['DEFAULT'].getint('clamav_port')

            if not self.clamav_host or not self.clamav_port:
                print("[WARN] ClamAV host or port is missing in config.ini. Scanning will fail.")
            else:
                print(f"[INFO] ClamAV agent loaded from config: {self.clamav_host}:{self.clamav_port}")

        except FileNotFoundError:
            print("[WARN] config.ini not found. Virus scanning will be disabled.")
            print("[WARN] Please create config.ini to enable scanning.")
        except Exception as e:
            print(f"[ERROR] Could not read config.ini: {e}")

    def set_clamav(self, host, port=6789):
        """Sets the address for the ClamAV scanning agent."""
        self.clamav_host = host
        self.clamav_port = port
        print(f"[OK] ClamAV agent address set to {self.clamav_host}:{self.clamav_port}")

    def connect(self, host, port=21):
        """
        Establishes a connection to the FTP server and handles user authentication.

        This method initializes the control connection socket, connects to the
        specified host and port, prompts the user for credentials, and
        attempts to log in. Upon successful login, it sets the client's
        connection status and changes the working directory to 'ftp' on the server.

        Args:
            host (str): The hostname or IP address of the FTP server.
            port (int, optional): The port number to connect to. Defaults to 21 (standard FTP port).

        Raises:
            Exception: If the login attempt fails (e.g., incorrect credentials or server error).
            socket.error: If there's an issue establishing the socket connection.
        """
        # Set FTP server host
        self.host = host
        # socket.AF_INET: Chỉ định rằng đây là một socket internet sử dụng địa chỉ IPv4.
        # socket.SOCK_STREAM: Sử dụng TCP, FTP là truyền file cần độ tin cậy
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Thiết lập kết nối TCP đến địa chỉ và cổng của máy chủ FTP
        self.control_sock.connect((host, port))
        self._recv_response_blocking()

        user = input("Username: ")
        passwd = input("Password: ")

        self._send_cmd(f"USER {user}")
        resp = self._recv_response_blocking()
        if resp.startswith('331'):
            self._send_cmd(f"PASS {passwd}")
            resp = self._recv_response_blocking()

        if not resp.startswith('230'):
            raise Exception("Login failed.")

        self.connected = True
        print(f"Connected to {host}:{port} as {user}")

        if not self.local_test_mode and self.host != '127.0.0.1':
            self.cd('ftp')

    def disconnect(self):
        """Disconnects from the FTP server.

        Sends the QUIT command to the server, closes the control socket, and updates
        connection state. Any errors during QUIT or close are suppressed to prevent
        crashing.
        """
        if self.control_sock:
            try:
                self._send_cmd("QUIT")
                print(self._recv_response_blocking())
            except:
                pass
            self.control_sock.close()
            self.control_sock = None
            self.connected = False
            print("Disconnected from server.")

    def _send_cmd(self, cmd):
        """
        Sends a command string to the FTP server over the control connection.

        This is a helper method that appends the necessary FTP line ending (\r\n),
        encodes the command string into bytes, and then sends it entirely
        to the server through the control socket.

        Args:
            cmd (str): The FTP command string to send (e.g., "USER myuser", "PASV", "RETR myfile.txt").
        """
        # helper method đóng vai trò là giao diện chính để gửi các lệnh điều khiển từ client đến máy chủ FTP
        # Tiêu chuẩn FTP: mỗi lệnh phải được kết thúc bằng một cặp ký tự Carriage Return (CR) theo sau bởi Line Feed (LF).
        # Encode cmd string thành bytes để gửi
        self.control_sock.sendall((cmd + '\r\n').encode())

    def _recv_response_blocking(self):
        """Receives a response from the FTP server, blocking until complete.

        Waits for data on the control socket until a complete FTP response is received.

        Returns:
            str: The decoded server response.

        Exceptions:
            socket.timeout: If no response is received within the set timeout.
            Exception: Any socket-related errors.
        """
        self.control_sock.settimeout(5)
        try:
            data = b""
            while True:
                part = self.control_sock.recv(BUFFER_SIZE)
                data += part
                # A simple way to detect the end of a multi-line FTP response
                if len(part) < BUFFER_SIZE and (data.endswith(b'\r\n') or not part):
                    break
            decoded_data = data.decode().strip()
            # print(f"[SERVER RESPONSE]\n---\n{decoded_data}\n---")
            return decoded_data
        except socket.timeout:
            print("[ERROR] Timeout receiving response")
            return "[ERROR] Timeout receiving response"
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            return f"[ERROR] {str(e)}"

    def _open_data_connection(self):
        """Opens a data connection for file transfers or directory listings.

        Chooses passive mode (EPSV/PASV) or active mode (PORT) based on configuration.

        Returns:
            socket.socket|None: The data connection socket in passive mode, or None in active mode (waiting for accept).

        Raises:
            Exception: If neither EPSV nor PASV succeeds in passive mode, or if PORT fails in active mode.
        """
        if self.passive_mode:
            # --- Modern Approach: Try EPSV first ---
            try:
                self._send_cmd("EPSV")
                resp = self._recv_response_blocking()
                debug_logger.debug(f"EPSV response: {resp}")

                if not resp.startswith('229'):
                    raise Exception("Server does not support EPSV, falling back.")

                # The EPSV response is like: "229 Entering Extended Passive Mode (|||64311|)"
                match = re.search(r'\((\|\|\|(\d+)\|)\)', resp)
                if not match:
                    raise Exception("Cannot parse EPSV response")
                
                port = int(match.group(2))
                
                # For the data connection, we connect to the SAME HOST as the control connection.
                data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data_sock.connect((self.host, port))
                return data_sock
            except Exception as e:
                print(f"[WARN] EPSV failed: {e}. Trying legacy PASV.")
                
                self._send_cmd("PASV")
                resp = self._recv_response_blocking()
                debug_logger.debug(f"[DEBUG] PASV response: {resp}")  # debug thêm
                if not resp.startswith('227'):
                    raise Exception(f"PASV failed: {resp}")
                match = re.search(r'\((.*?)\)', resp)
                if not match:
                    raise Exception("PASV response format invalid")
                numbers = match.group(1).split(',')
                if len(numbers) != 6:
                    raise Exception("Invalid PASV address data")
                ip = '.'.join(numbers[:4])
                port = (int(numbers[4]) << 8) + int(numbers[5])
                data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                data_sock.connect((ip, port))
                return data_sock
        # Active Mode
        else:
            if self.local_test_mode:
                # Dùng loopback IP cho test mode
                # Khi này FTP client và FTP server đều chạy trên cùng một máy
                ip = "127.0.0.1"
            else:
                # Tạo temporary UDP socket để lấy private IP của FTP client
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    # Kết nối ra ngoài (Google DNS)
                    s.connect(("8.8.8.8", 80))
                    # Lấy IP của chính socket mà hệ điều hành dùng để gửi gói tin ra (Private IP của máy)
                    ip = s.getsockname()[0]
                finally:
                    # Đã lấy được private IP, đóng kết nối
                    s.close()
                    
            # Tạo TCP socket
            self.active_data_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Ràng buộc nó với một cổng ngẫu nhiên do hệ điều hành cấp phát
            self.active_data_listener.bind(('', 0))
            # Bắt đầu lắng nghe, settimeout tránh treo mãi nếu server không connect lại
            self.active_data_listener.settimeout(10)
            # Cho phép 1 kết nối
            self.active_data_listener.listen(1)
            # Lấy port ngẫu nhiên được tạo trước đó
            port = self.active_data_listener.getsockname()[1]
            debug_logger.debug(f"[DEBUG] Active mode: Sending PORT with IP = {ip}, Port = {port}")
            
            # Nếu ip là "192.168.1.10", thì ip.split('.') sẽ trả về ['192', '168', '1', '10']
            # Lệnh PORT trong FTP yêu cầu địa chỉ IP được truyền dưới dạng bốn số nguyên được phân tách bằng dấu phẩy
            ip_nums = ip.split('.')
            # p1 là "byte cao" (most significant byte) của port
            p1 = port >> 8
            # p2 là "byte thấp" (least significant byte) của port
            p2 = port & 0xFF

            # Lệnh PORT: gửi từ FTP client đến FTP server khi client muốn thiết lập một kênh dữ liệu ở chế độ Active.
            # Server sẽ tính lại port từ p1 và p2: port = (p1 * 256) + p2
            self._send_cmd(f"PORT {','.join(ip_nums)},{p1},{p2}")
            resp = self._recv_response_blocking()
            
            # "200 Command okay."
            if not resp.startswith('200'):
                # Clean up nếu connection không thành công
                self.active_data_listener.close()
                self.active_data_listener = None
                raise Exception(f"PORT failed: {resp}")
            return None  # chủ động trả về None để phân biệt

    def status(self):
        """Prints the current FTP client status, including mode and connection state."""
        print("Passive Mode:", self.passive_mode)
        print("Transfer Mode:", self.transfer_mode)
        print("Test Mode:", "On" if self.local_test_mode else "Off")

    def toggle_prompt(self):
        """Toggles the user prompt for mget/mput operations."""
        self.prompt = not self.prompt
        print(f"Prompt mode {'enabled' if self.prompt else 'disabled'}")

    def set_ascii(self):
        """Sets the file transfer mode to ASCII and informs the server."""
        self.transfer_mode = 'ascii'
        self._send_cmd("TYPE A")
        resp = self._recv_response_blocking()
        
        # Check if the server confirmed the command successfully (response code 200)
        if resp.startswith('200'):
            # Only change the client's internal state AFTER server confirmation
            self.transfer_mode = 'ascii'
            print("[OK] Transfer mode set to ASCII.")
        else:
            # If it fails, inform the user with the server's error message
            print(f"[ERROR] Failed to set ASCII mode: {resp}")

    def set_binary(self):
        """Sets the file transfer mode to Binary and informs the server."""
        self.transfer_mode = 'binary'
        self._send_cmd("TYPE I")
        resp = self._recv_response_blocking()

        # Check if the server confirmed the command successfully (response code 200)
        if resp.startswith('200'):
            # Only change the client's internal state AFTER server confirmation
            self.transfer_mode = 'binary'
            print("[OK] Transfer mode set to Binary.")
        else:
            # If it fails, inform the user with the server's error message
            print(f"[ERROR] Failed to set Binary mode: {resp}")


    def toggle_passive(self):
        """Toggles passive mode on or off."""
        self.passive_mode = not self.passive_mode
        print(f"Passive mode {'enabled' if self.passive_mode else 'disabled'}")

    def ls(self):
        """Lists files on the server in the current working directory.

        Uses LIST command over a data connection in passive or active mode.
        Prints the directory listing to stdout.
        """
        try:
            if self.passive_mode:
                data_sock = self._open_data_connection()
            else:
                self._open_data_connection()

            self._send_cmd("LIST")
            resp = self._recv_response_blocking()
            if not resp.startswith("150"):
                print(f"[ERROR] {resp}")
                if self.passive_mode:
                    data_sock.close()
                else:
                    self.active_data_listener.close()
                    self.active_data_listener = None
                return

            if not self.passive_mode:
                try:
                    data_sock, _ = self.active_data_listener.accept()
                except socket.timeout:
                    print("[ERROR] Timeout waiting for server to connect in active mode.")
                    self.active_data_listener.close()
                    self.active_data_listener = None
                    return
                self.active_data_listener.close()
                self.active_data_listener = None


            while True:
                data = data_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                print(data.decode(), end='')

            data_sock.close()
            print(self._recv_response_blocking())

        except Exception as e:
            print(f"[ERROR] {str(e)}")

    def cd(self, path):
        """Changes the current working directory on the server.

        Args:
            path (str): Target directory path on the server.
        """
        self._send_cmd(f"CWD {path}")
        resp = self._recv_response_blocking()
        if resp.startswith("250"):
            print(f"[OK] {resp}")
        else:
            print(f"[ERROR] {resp}")


    def pwd(self):
        """Prints the current working directory on the server."""
        self._send_cmd("PWD")
        print(self._recv_response_blocking())

    def mkdir(self, dirname):
        """Creates a directory on the server.

        Args:
            dirname (str): Name of the directory to create.
        """
        self._send_cmd(f"MKD {dirname}")
        resp = self._recv_response_blocking()
        # if resp.startswith("257"):
        #     print(f"[OK] {resp}")
        # else:
        #     print(f"[ERROR] {resp}")
        print(f"Response: {resp}")

    def rmdir(self, dirname):
        """Removes a directory on the server.

        Args:
            dirname (str): Name of the directory to remove.
        """
        self._send_cmd(f"RMD {dirname}")
        resp = self._recv_response_blocking()
        print(f"Response: {resp}")
        # if resp.startswith("250"):
        #     print(f"[OK] {resp}")
        # else:
        #     print(f"[ERROR] {resp}")

    def delete(self, filename):
        """Deletes a file on the server.

        Args:
            filename (str): Name of the file to delete.
        """
        self._send_cmd(f"DELE {filename}")
        print(self._recv_response_blocking())

    def rename(self, from_name, to_name):
        """Renames a file on the server.

        Args:
            from_name (str): Current file name.
            to_name (str): New file name.
        """
        self._send_cmd(f"RNFR {from_name}")
        resp = self._recv_response_blocking()
        if resp.startswith('350'):
            self._send_cmd(f"RNTO {to_name}")
            print(self._recv_response_blocking())
        else:
            print(resp)

    def get(self, filename, destination_path=None):
        """Downloads a file from the server.

        Args:
            filename (str): Name of the file to download.
            destination_path (str|None): Local path or directory to save the file.
        """
        if destination_path:
            if os.path.isdir(destination_path):
                local_path = os.path.join(destination_path, os.path.basename(filename))
            else:
                local_path = destination_path
        else:
            local_path = os.path.basename(filename)

        try:
            data_sock = None # Initialize to None
            if self.passive_mode:
                data_sock = self._open_data_connection()
            else:
                self._open_data_connection()
                self._send_cmd(f"RETR {filename}")  # GỬI TRƯỚC KHI accept()
                resp = self._recv_response_blocking()
                if not resp.startswith('150'):
                    print(f"[ERROR] {resp}")
                    return
                try:
                    data_sock, _ = self.active_data_listener.accept()
                except socket.timeout:
                    print("[ERROR] Timeout waiting for server to connect in active mode.")
                    self.active_data_listener.close()
                    self.active_data_listener = None
                    return
                self.active_data_listener.close()
                self.active_data_listener = None

            if data_sock is None and self.passive_mode:
                print("[ERROR] Failed to establish a data socket in passive mode.")
                return

            if self.passive_mode:
                self._send_cmd(f"RETR {filename}")
                resp = self._recv_response_blocking()
                if not resp.startswith('150'):
                    print(f"[ERROR] Server did not respond with '150 File status okay'. Aborting download.")
                    print(f"[ERROR] {resp}")
                    if data_sock:
                        data_sock.close()
                    return

            # debug_logger.debug(f"[DEBUG] Server is ready to send. Receiving data into '{local_path}'...")
            os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
            with open(local_path, 'wb') as f:
                while True:
                    data = data_sock.recv(BUFFER_SIZE)
                    if not data:
                        break
                    if self.transfer_mode == 'ascii':
                        data = data.replace(b'\r\n', b'\n')
                    f.write(data)
            data_sock.close()
            print(self._recv_response_blocking())
            print(f"Downloaded {filename} -> {local_path}")

        except Exception as e:
            print(f"[ERROR] {str(e)}")

    def make_remote_dirs(self, path):
        """Creates nested directories on the server.

        Args:
            path (str): Path to create on the server.
        """
        dirs = path.replace("\\", "/").split("/")
        curr = ""
        for d in dirs:
            if not d:
                continue
            curr = f"{curr}/{d}" if curr else d
            self._send_cmd(f"MKD {curr}")
            resp = self._recv_response_blocking()
            if not resp.startswith("257") and not "File exists" in resp:
                if not resp.startswith("550"):
                    print(f"[WARN] Failed to create remote dir '{curr}': {resp}")

    def put(self, filepath, remote_rel_path=""):
        """Uploads a file to the server after scanning with ClamAV.

        Args:
            filepath (str): Local path of the file to upload.
            remote_rel_path (str): Relative remote path to store the file.
        """
        if not os.path.isfile(filepath):
            print(f"[ERROR] File '{filepath}' does not exist.")
            return
        result = self.scan_with_clamav(filepath)
        if result != "OK":
            print(f"[WARNING] Upload aborted. Scan result: {result}")
            return
        try:
            remote_path = os.path.join(remote_rel_path, os.path.basename(filepath)).replace('\\', '/')
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self.make_remote_dirs(remote_dir)

            if self.passive_mode:
                data_sock = self._open_data_connection()
                self._send_cmd(f"STOR {remote_path}")
                resp = self._recv_response_blocking()
                if not resp.startswith('150'):
                    print(f"[ERROR] {resp}")
                    return
            # Put - Active mode
            else:
                # Thiết lập kênh Active tới FTP client
                self._open_data_connection()
                # Lệnh này yêu cầu máy chủ tạo hoặc ghi đè một file trên hệ thống của nó với tên là <remote_path> và chuẩn bị nhận dữ liệu cho file đó.
                # STOR: client gửi data
                self._send_cmd(f"STOR {remote_path}")  # Gửi STOR TRƯỚC khi accept
                resp = self._recv_response_blocking()
                if not resp.startswith('150'):
                    print(f"[ERROR] {resp}")
                    return
                try:
                    # Chặn thực thi chương trình cho đến khi máy chủ FTP tạo một kết nối đến socket đang lắng nghe của client
                    data_sock, _ = self.active_data_listener.accept()
                # Cơ chế khi chờ quá lâu
                except socket.timeout:
                    print("[ERROR] Timeout waiting for server to connect in active mode.")
                    self.active_data_listener.close()
                    self.active_data_listener = None
                    return
                # Socket từ client đến server không cần thiết nữa, chỉ gửi dữ liệu qua socket từ server tới client
                self.active_data_listener.close()
                self.active_data_listener = None

            # Client mở file cục bộ (filepath) ở chế độ nhị phân ('rb')
            with open(filepath, 'rb') as f:
                while True:
                    # Trong vòng lặp, client đọc từng khối dữ liệu (BUFFER_SIZE bytes) từ file.
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    if self.transfer_mode == 'ascii':
                        # Nếu transfer_mode là ascii, thay thế \n (Line Feed) bằng cặp \r\n (Carriage Return + Line Feed). 
                        # Đây là yêu cầu của FTP khi truyền file văn bản ở chế độ ASCII để đảm bảo tính tương thích giữa các OS.
                        data = data.replace(b'\n', b'\r\n')
                    # Gửi data
                    data_sock.sendall(data)
            # Đóng data channel khi đã hoàn tất gửi
            data_sock.close()
            
            # Phản hồi từ server
            print(self._recv_response_blocking())
            # In kết quả ra terminal cho user
            print(f"Uploaded {filepath} -> {remote_path}")
        except Exception as e:
            print(f"[ERROR] {str(e)}")

    def mput(self, args):
        """Uploads multiple files matching a pattern.

        Args:
            args (str): File pattern or directory for upload.
        """
        import glob
        parts = args.strip().split()
        uploaded = set()

        def collect_files(path, base_dir=""):
            if os.path.isfile(path):
                yield (path, base_dir)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    rel_path = os.path.relpath(root, base_dir or os.path.dirname(path))
                    for f in files:
                        yield (os.path.join(root, f), rel_path)

        for part in parts:
            matches = glob.glob(part, recursive=True)
            for match in matches:
                for local_path, rel_path in collect_files(match):
                    norm = os.path.normpath(local_path)
                    if norm in uploaded:
                        continue
                    uploaded.add(norm)
                    if self.prompt:
                        ans = input(f"Upload {local_path}? (y/n): ")
                        if ans.lower() != 'y':
                            continue
                    self.put(local_path, rel_path)


    def mget(self, args):
        """Downloads multiple files matching a pattern or directory.

        Args:
            args (str): Remote file pattern or directory.
        """
        parts = args.strip().split()
        dest_dir = "."

        if parts and os.path.isdir(parts[-1]):
            dest_dir = parts[-1]
            parts = parts[:-1]

        def is_directory(remote_path):
            self._send_cmd(f"CWD {remote_path}")
            resp = self._recv_response_blocking()
            if resp.startswith("250"):
                self._send_cmd("CDUP")
                self._recv_response_blocking()
                return True
            return False

        def parse_listing(listing):
            entries = []
            for line in listing.decode().splitlines():
                parts = line.split()
                if len(parts) < 9:
                    continue
                name = parts[-1]
                type_char = parts[0][0]
                entries.append((name, type_char == 'd'))
            return entries

        def recursive_download(remote_path, local_path):
            os.makedirs(local_path, exist_ok=True)

            if self.passive_mode:
                data_sock = self._open_data_connection()
                self._send_cmd(f"LIST {remote_path}")
                resp = self._recv_response_blocking()
                if not resp.startswith("150"):
                    print(f"[ERROR] {resp}")
                    return
            else:
                self._open_data_connection()
                self._send_cmd(f"LIST {remote_path}")
                resp = self._recv_response_blocking()
                if not resp.startswith("150"):
                    print(f"[ERROR] {resp}")
                    return
                try:
                    data_sock, _ = self.active_data_listener.accept()
                except socket.timeout:
                    print("[ERROR] Timeout waiting for server to connect in active mode.")
                    self.active_data_listener.close()
                    self.active_data_listener = None
                    return
                self.active_data_listener.close()
                self.active_data_listener = None

            listing = b""
            while True:
                chunk = data_sock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                listing += chunk
            data_sock.close()
            self._recv_response_blocking()

            for name, is_dir in parse_listing(listing):
                remote_item = f"{remote_path}/{name}".replace("//", "/")
                local_item = os.path.join(local_path, name)
                if is_dir:
                    if self.prompt:
                        ans = input(f"Download directory {remote_item}? (y/n): ")
                        if ans.lower() != 'y':
                            continue
                    recursive_download(remote_item, local_item)
                else:
                    if self.prompt:
                        ans = input(f"Download file {remote_item}? (y/n): ")
                        if ans.lower() != 'y':
                            continue
                    self.get(remote_item, local_item)

        def match_remote_files(pattern):
            data_sock = self._open_data_connection()
            self._send_cmd("LIST")
            resp = self._recv_response_blocking()
            if not resp.startswith("150"):
                print(f"[ERROR] {resp}")
                return []
            listing = b""
            while True:
                chunk = data_sock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                listing += chunk
            data_sock.close()
            self._recv_response_blocking()

            matched = []
            for name, is_dir in parse_listing(listing):
                if fnmatch.fnmatch(name, pattern):
                    matched.append((name, is_dir))
            return matched

        for target in parts:
            if "*" in target or "?" in target:
                matched_files = match_remote_files(os.path.basename(target))
                prefix = os.path.dirname(target)
                for name, is_dir in matched_files:
                    remote_path = f"{prefix}/{name}" if prefix else name
                    local_path = os.path.join(dest_dir, name)
                    if is_dir:
                        if self.prompt:
                            ans = input(f"Download directory {remote_path}? (y/n): ")
                            if ans.lower() != 'y':
                                continue
                        recursive_download(remote_path, os.path.join(dest_dir, name))
                    else:
                        if self.prompt:
                            ans = input(f"Download file {remote_path}? (y/n): ")
                            if ans.lower() != 'y':
                                continue
                        self.get(remote_path, local_path)
            else:
                if is_directory(target):
                    local_target_dir = os.path.join(dest_dir, os.path.basename(target))
                    recursive_download(target, local_target_dir)
                else:
                    local_file = os.path.join(dest_dir, os.path.basename(target))
                    if self.prompt:
                        ans = input(f"Download file {target}? (y/n): ")
                        if ans.lower() != 'y':
                            continue
                    self.get(target, local_file)

    def scan_with_clamav(self, filepath):
        """Scans a file with ClamAV before upload.

        Args:
            filepath (str): Path to the local file.

        Returns:
            str: Scan result string.
        """
        if not self.clamav_host:
            return "ERROR: ClamAV agent address is not configured. Please create a valid config.ini file."

        # START progress bar
        s = None # Define s here to access it in the finally block
        spinner_thread = None
        stop_spinner = threading.Event() # Event to signal the spinner thread to stop

        try:
            filesize = os.path.getsize(filepath)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.clamav_host, self.clamav_port))
            metadata = f"{os.path.basename(filepath)}:{filesize}"
            s.sendall(metadata.encode())
            ack = s.recv(1024)
            if ack != b"META_OK":
                s.close()
                return "ERROR: ClamAVAgent did not acknowledge metadata."
            
            # --- Phase 1: Determinate Progress (Uploading) ---
            bytes_sent = 0
            progress_bar_length = 50
            send_pretext = f"Sending to ClamAV: '{os.path.basename(filepath)}':"

            sys.stdout.write(send_pretext)
            sys.stdout.flush()

            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    s.sendall(data)
                    bytes_sent += len(data)

                    # Calculate progress
                    percent_complete = (bytes_sent / filesize) * 100
                    filled_length = int(progress_bar_length * bytes_sent // filesize)
                    bar = '█' * filled_length + '-' * (progress_bar_length - filled_length)
                        
                    progress_string = f'\r{send_pretext} |{bar}| {percent_complete:.2f}%'
                    sys.stdout.write(progress_string)
                    sys.stdout.flush()
                    
                    # Add a small delay to visualize the progress
                    time.sleep(0.01)
                    
            # --- Phase 2: Indeterminate Progress (Waiting for Scan) ---
            # Start the spinner thread
            sys.stdout.write('\n')
            spinner_thread = threading.Thread(target=self._spinner_animation, args=(stop_spinner,))
            sys.stdout.write("Waiting for scan result: ")
            spinner_thread.start()

            # The main thread blocks here, waiting for the server's response
            # The spinner thread continues to run in the background

            result = s.recv(1024).decode()
            
            # Stop the spinner and print "Done" on the same line.
            if spinner_thread.is_alive():
                stop_spinner.set()
                spinner_thread.join()
                sys.stdout.write("Done\n")
                sys.stdout.flush()
            
            # Explain the result to the user
            if result == "OK":
                print(f"Result OK: The file is safe.")
            elif result == "INFECTED":
                print(f"Result INFECTED: The file contains virus.")
            elif result.startswith("ERROR"):
                print(f"Result ERROR: {result}")
            else:
                print(f"Result UNKNOWN: {result}")

            return result
        except Exception as e:
            # On error, ensure the spinner is stopped before printing the error
            if spinner_thread and spinner_thread.is_alive():
                stop_spinner.set()
                spinner_thread.join()
                sys.stdout.write("Failed\n")
            return f"ERROR: {str(e)}"
        finally:
            # --- Cleanup Phase ---
            # Failsafe to ensure the thread is stopped, though it should be already.
            if spinner_thread and spinner_thread.is_alive():
                stop_spinner.set()
                spinner_thread.join()

            if s:
                s.close()

    def help(self):
        """Prints the list of supported FTP client commands."""
        print("""
Supported Commands:
  open <host> [port]        Connect to FTP server
  close                     Disconnect from FTP server
  status                    Show connection status
  passive                   Toggle passive mode
  ascii                     Set ASCII mode
  binary                    Set binary mode
  prompt                    Toggle prompt for mput/mget
  ls                        List files on server
  cd <dir>                  Change server directory
  pwd                       Print working directory
  mkdir <name>              Create server directory
  rmdir <name>              Remove server directory
  delete <file>             Delete file on server
  rename <from> <to>        Rename file on server
  get, recv <file> [dest]         Download file
  mget <pattern> [dest]     Download multiple files
  put <file>                Upload file (scan first)
  mput <pattern>            Upload multiple files (scan all)
  help, ?                   Show this help
  quit, bye                 Exit the client
  testmode on/off           Set test mode: on-local/off-remote
""")

def main():
    client = RawFTPClient()
    client.load_config()

    while True:
        try:
            command = input("ftp> ").strip()
            if not command:
                continue
            parts = command.split()
            cmd = parts[0].lower()

            if cmd in ('quit', 'bye'):
                client.disconnect()
                break
            elif cmd == 'open':
                if len(parts) < 2:
                    print("[ERROR] Missing host for 'open'")
                else:
                    port = int(parts[2]) if len(parts) > 2 else 21
                    client.connect(parts[1], port)
            elif cmd == 'close':
                client.disconnect()
            elif cmd == 'status':
                client.status()
            elif cmd == 'passive':
                client.toggle_passive()
            elif cmd == 'testmode':
                if len(parts) == 2 and parts[1].lower() == 'on':
                    client.local_test_mode = True
                    print("[INFO] Local test mode enabled (using 127.0.0.1 for active mode)")
                elif len(parts) == 2 and parts[1].lower() == 'off':
                    client.local_test_mode = False
                    print("[INFO] Local test mode disabled (using real IP for active mode)")
                else:
                    print("[ERROR] Usage: testmode on/off")
            elif cmd == 'ascii':
                client.set_ascii()
            elif cmd == 'binary':
                client.set_binary()
            elif cmd == 'prompt':
                client.toggle_prompt()
            elif cmd == 'ls':
                client.ls()
            elif cmd == 'cd':
                if len(parts) < 2:
                    print("[ERROR] Missing directory path for 'cd'")
                else:
                    client.cd(parts[1])
            elif cmd == 'pwd':
                client.pwd()
            elif cmd == 'mkdir':
                if len(parts) < 2:
                    print("[ERROR] Missing name for 'mkdir'")
                else:
                    client.mkdir(parts[1])
            elif cmd == 'rmdir':
                if len(parts) < 2:
                    print("[ERROR] Missing name for 'rmdir'")
                else:
                    client.rmdir(parts[1])
            elif cmd == 'delete':
                if len(parts) < 2:
                    print("[ERROR] Missing file name for 'delete'")
                else:
                    client.delete(parts[1])
            elif cmd == 'rename':
                if len(parts) < 3:
                    print("[ERROR] Usage: rename <from> <to>")
                else:
                    client.rename(parts[1], parts[2])
            elif cmd in ('get', 'recv'):
                if len(parts) == 2:
                    client.get(parts[1])
                elif len(parts) == 3:
                    client.get(parts[1], parts[2])
                else:
                    print("[ERROR] Usage: get <file> [destination]")
            elif cmd == 'put':
                if len(parts) < 2:
                    print("[ERROR] Missing file name for 'put'")
                else:
                    client.put(parts[1])
            elif cmd == 'mput':
                args = command[len('mput'):].strip()
                if not args:
                    print("[ERROR] Missing pattern for 'mput'")
                else:
                    client.mput(args)
            elif cmd == 'mget':
                args = command[len('mget'):].strip()
                if not args:
                    print("[ERROR] Missing pattern for 'mget'")
                else:
                    client.mget(args)
            elif cmd in ('help', '?'):
                client.help()
            else:
                print(f"[ERROR] Unknown command: {cmd}")
        except Exception as e:
            print(f"[ERROR] {str(e)}")


if __name__ == '__main__':
    main()
