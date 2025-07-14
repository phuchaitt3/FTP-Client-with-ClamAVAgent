import os
import socket
import fnmatch
import glob
import re

CLAMAV_HOST = '127.0.0.1'
CLAMAV_PORT = 6789
BUFFER_SIZE = 4096

class RawFTPClient:
    def __init__(self):
        self.control_sock = None
        self.passive_mode = True
        self.transfer_mode = 'binary'
        self.prompt = True
        self.connected = False
        self.host = None

    def connect(self, host, port=21):
        self.host = host
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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

    def disconnect(self):
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
        self.control_sock.sendall((cmd + '\r\n').encode())

    def _recv_response_blocking(self):
        self.control_sock.settimeout(5)
        try:
            data = b""
            while True:
                part = self.control_sock.recv(BUFFER_SIZE)
                data += part
                if len(part) < BUFFER_SIZE:
                    break
            return data.decode().strip()
        except socket.timeout:
            return "[ERROR] Timeout receiving response"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _open_data_connection(self):
        if self.passive_mode:
            # Passive mode (giữ nguyên)
            self._send_cmd("PASV")
            resp = self._recv_response_blocking()
            if not resp.startswith('227'):
                raise Exception("PASV failed")
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
        else:
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.bind(('', 0))
            data_sock.listen(1)

            # Lấy IP LAN thực tế
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()

            port = data_sock.getsockname()[1]
            print(f"[DEBUG] Active mode: Using IP = {ip}, Port = {port}")

            ip_nums = ip.split('.')
            p1 = port >> 8
            p2 = port & 0xFF
            self._send_cmd(f"PORT {','.join(ip_nums)},{p1},{p2}")
            resp = self._recv_response_blocking()
            if not resp.startswith('200'):
                data_sock.close()
                raise Exception(f"PORT failed: {resp}")
            conn, _ = data_sock.accept()
            data_sock.close()
            return conn



    def status(self):
        print("Passive Mode:", self.passive_mode)
        print("Transfer Mode:", self.transfer_mode)
        print("Connected:", self.connected)

    def toggle_prompt(self):
        self.prompt = not self.prompt
        print(f"Prompt mode {'enabled' if self.prompt else 'disabled'}")

    def set_ascii(self):
        self.transfer_mode = 'ascii'
        self._send_cmd("TYPE A")
        resp = self._recv_response_blocking()
        print(resp if resp else "Transfer mode set to ASCII")

    def set_binary(self):
        self.transfer_mode = 'binary'
        self._send_cmd("TYPE I")
        resp = self._recv_response_blocking()
        print(resp if resp else "Transfer mode set to Binary")


    def toggle_passive(self):
        self.passive_mode = not self.passive_mode
        print(f"Passive mode {'enabled' if self.passive_mode else 'disabled'}")

    def ls(self):
        try:
            data_sock = self._open_data_connection()
            self._send_cmd("LIST")
            resp = self._recv_response_blocking()
            if not resp.startswith("150"):
                print(f"[ERROR] {resp}")
                data_sock.close()
                return
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
        self._send_cmd(f"CWD {path}")
        resp = self._recv_response_blocking()
        if resp.startswith("250"):
            print(f"[OK] {resp}")
        else:
            print(f"[ERROR] {resp}")


    def pwd(self):
        self._send_cmd("PWD")
        print(self._recv_response_blocking())

    def mkdir(self, dirname):
        self._send_cmd(f"MKD {dirname}")
        resp = self._recv_response_blocking()
        if resp.startswith("257"):
            print(f"[OK] {resp}")
        else:
            print(f"[ERROR] {resp}")

    def rmdir(self, dirname):
        self._send_cmd(f"RMD {dirname}")
        resp = self._recv_response_blocking()
        if resp.startswith("250"):
            print(f"[OK] {resp}")
        else:
            print(f"[ERROR] {resp}")

    def delete(self, filename):
        self._send_cmd(f"DELE {filename}")
        print(self._recv_response_blocking())

    def rename(self, from_name, to_name):
        self._send_cmd(f"RNFR {from_name}")
        resp = self._recv_response_blocking()
        if resp.startswith('350'):
            self._send_cmd(f"RNTO {to_name}")
            print(self._recv_response_blocking())
        else:
            print(resp)

    def get(self, filename, destination_path=None):
        if destination_path:
            if os.path.isdir(destination_path):
                local_path = os.path.join(destination_path, os.path.basename(filename))
            else:
                local_path = destination_path
        else:
            local_path = os.path.basename(filename)

        try:
            data_sock = self._open_data_connection()
            self._send_cmd(f"RETR {filename}")
            resp = self._recv_response_blocking()
            if not resp.startswith('150'):
                print(f"[ERROR] {resp}")
                data_sock.close()
                return
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
                self.make_remote_dirs(remote_dir)  # tạo thư mục đệ quy

            data_sock = self._open_data_connection()
            self._send_cmd(f"STOR {remote_path}")
            resp = self._recv_response_blocking()
            if not resp.startswith('150'):
                print(f"[ERROR] {resp}")
                data_sock.close()
                return
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    if self.transfer_mode == 'ascii':
                        data = data.replace(b'\n', b'\r\n')
                    data_sock.sendall(data)
            data_sock.close()
            print(self._recv_response_blocking())
            print(f"Uploaded {filepath} -> {remote_path}")
        except Exception as e:
            print(f"[ERROR] {str(e)}")

    def mput(self, args):
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
            data_sock = self._open_data_connection()
            self._send_cmd(f"LIST {remote_path}")
            resp = self._recv_response_blocking()
            if not resp.startswith("150"):
                print(f"[ERROR] {resp}")
                return
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
        try:
            filesize = os.path.getsize(filepath)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((CLAMAV_HOST, CLAMAV_PORT))
            metadata = f"{os.path.basename(filepath)}:{filesize}"
            s.sendall(metadata.encode())
            ack = s.recv(1024)
            if ack != b"META_OK":
                s.close()
                return "ERROR: ClamAVAgent did not acknowledge metadata."
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    s.sendall(data)
            result = s.recv(1024).decode()
            s.close()
            return result
        except Exception as e:
            return f"ERROR: {str(e)}"

    def help(self):
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
  get <file> [dest]         Download file
  mget <pattern> [dest]     Download multiple files
  put <file>                Upload file (scan first)
  mput <pattern>            Upload multiple files (scan all)
  help, ?                   Show this help
  quit, bye                 Exit the client
""")

def main():
    client = RawFTPClient()
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
            elif cmd == 'get':
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
