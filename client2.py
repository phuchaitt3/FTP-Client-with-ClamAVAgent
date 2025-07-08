import os
import socket
import ftplib
import fnmatch
from ftplib import FTP_TLS
CLAMAV_HOST = '127.0.0.1'
CLAMAV_PORT = 6789

class FTPClient:
    def __init__(self):
        self.ftp = None
        self.passive_mode = True
        self.transfer_mode = 'binary'
        self.prompt = True

    def connect(self, host, port=21):
        try:
            self.ftp = FTP_TLS()
            user = input("Username: ")
            passwd = input("Password: ")
            self.ftp.connect(host, port)
            self.ftp.auth()
            self.ftp.login(user=user, passwd=passwd)
            self.ftp.prot_p()
            self.ftp.set_pasv(self.passive_mode)

            print(f"Connected securely to {host}:{port} as {user}")
        except error_perm as e:
            print(f"[AUTH ERROR] {e}")
        except Exception as e:
            print(f"[ERROR] {e}")

    def disconnect(self):
        if self.ftp:
            self.ftp.quit()
            print("Disconnected from server.")

    def status(self):
        print("Passive Mode:", self.passive_mode)
        print("Transfer Mode:", self.transfer_mode)
        print("Connected:", self.ftp is not None)

    def toggle_prompt(self):
        self.prompt = not self.prompt
        print(f"Prompt mode {'enabled' if self.prompt else 'disabled'}")

    def set_ascii(self):
        self.transfer_mode = 'ascii'
        print("Transfer mode set to ASCII")

    def set_binary(self):
        self.transfer_mode = 'binary'
        print("Transfer mode set to Binary")

    def toggle_passive(self):
        self.passive_mode = not self.passive_mode
        if self.ftp:
            self.ftp.set_pasv(self.passive_mode)
        print(f"Passive mode {'enabled' if self.passive_mode else 'disabled'}")

    def ls(self):
        self.ftp.retrlines('LIST')

    def cd(self, path):
        self.ftp.cwd(path)

    def pwd(self):
        print(self.ftp.pwd())

    def mkdir(self, dirname):
        self.ftp.mkd(dirname)

    def rmdir(self, dirname):
        self.ftp.rmd(dirname)

    def delete(self, filename):
        self.ftp.delete(filename)

    def rename(self, from_name, to_name):
        self.ftp.rename(from_name, to_name)

    def get(self, filename, destination_path=None):
        if destination_path:
            # Nếu destination_path là thư mục, dùng tên gốc để lưu file
            if os.path.isdir(destination_path):
                local_path = os.path.join(destination_path, os.path.basename(filename))
            else:
                # Giả định destination_path là đường dẫn đầy đủ (bao gồm tên file mới)
                local_path = destination_path
        else:
            # Không truyền destination_path → dùng tên file gốc
            local_path = os.path.basename(filename)

        try:
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f"RETR {filename}", f.write)
            print(f"Downloaded {filename} -> {local_path}")
        except Exception as e:
            print(f"[ERROR] Failed to download {filename}: {str(e)}")


    def mget(self, args):
        import os

        args = args.strip().split()
        if not args:
            print("Usage: mget <file1> [file2|wildcard ...] [destination_dir]")
            return

        # Xác định thư mục đích (nếu có)
        potential_dest = args[-1]
        if os.path.isdir(potential_dest):
            dest_dir = os.path.normpath(potential_dest)
            patterns = args[:-1]
        else:
            dest_dir = "."
            patterns = args

        if not patterns:
            print("No files or patterns specified.")
            return

        def is_directory(name):
            try:
                current = self.ftp.pwd()
                self.ftp.cwd(name)
                self.ftp.cwd(current)  # quay về lại nếu thành công
                return True
            except Exception:
                return False


        def recursive_download(remote_path, local_path):
            """Tải đệ quy từ remote_path (trên server) vào local_path (trên máy)"""
            try:
                os.makedirs(local_path, exist_ok=True)
                file_list = []
                self.ftp.retrlines(f'LIST {remote_path}', file_list.append)
                for entry in file_list:
                    parts = entry.split()
                    if len(parts) < 9:
                        continue
                    name = parts[-1]
                    full_remote = f"{remote_path}/{name}"
                    full_local = os.path.join(local_path, name)
                    if entry.startswith('d'):
                        if self.prompt:
                            ans = input(f"Download directory {full_remote}? (y/n): ")
                            if ans.lower() != 'y':
                                continue
                        recursive_download(full_remote, full_local)
                    else:
                        if self.prompt:
                            ans = input(f"Download file {full_remote}? (y/n): ")
                            if ans.lower() != 'y':
                                continue
                        try:
                            with open(full_local, 'wb') as f:
                                self.ftp.retrbinary(f"RETR {full_remote}", f.write)
                            print(f"Downloaded {full_remote} -> {full_local}")
                        except Exception as e:
                            print(f"[ERROR] Failed to download {full_remote}: {str(e)}")
            except Exception as e:
                print(f"[ERROR] Cannot access directory {remote_path}: {e}")

        # Lặp qua từng pattern (tên cụ thể hoặc wildcard)
        for pattern in patterns:
            try:
                matched = self.ftp.nlst(pattern)
            except Exception as e:
                print(f"[ERROR] Pattern '{pattern}' failed: {e}")
                continue

            if not matched:
                print(f"[WARNING] No match for: {pattern}")
                continue

            for item in matched:
                if is_directory(item):
                    if self.prompt:
                        ans = input(f"Download directory {item}? (y/n): ")
                        if ans.lower() != 'y':
                            continue
                    recursive_download(item, os.path.join(dest_dir, os.path.basename(item)))
                else:
                    if self.prompt:
                        ans = input(f"Download file {item}? (y/n): ")
                        if ans.lower() != 'y':
                            continue
                    try:
                        target = os.path.join(dest_dir, os.path.basename(item))
                        with open(target, 'wb') as f:
                            self.ftp.retrbinary(f"RETR {item}", f.write)
                        print(f"Downloaded {item} -> {target}")
                    except Exception as e:
                        print(f"[ERROR] Failed to download {item}: {str(e)}")


    def put(self, filepath):
        if not os.path.isfile(filepath):
            print(f"File '{filepath}' does not exist.")
            return

        # First: scan file using ClamAVAgent
        result = self.scan_with_clamav(filepath)
        if result == "OK":
            with open(filepath, 'rb') as f:
                if self.transfer_mode == 'ascii':
                    self.ftp.storlines(f"STOR {os.path.basename(filepath)}", f)
                else:
                    self.ftp.storbinary(f"STOR {os.path.basename(filepath)}", f)
            print(f"Uploaded {filepath}")
        elif result == "INFECTED":
            print(f"[WARNING] File '{filepath}' is INFECTED. Upload aborted.")
        else:
            print(f"[ERROR] Scan failed: {result}")

    def mput(self, args):
        import glob

        args = args.strip()
        files = []

        if not args:
            # Không có tham số: upload tất cả các file trong thư mục hiện tại
            files = [os.path.join('.', f) for f in os.listdir('.') if os.path.isfile(f)]
        else:
            parts = args.split()
            for pattern in parts:
                pattern = os.path.normpath(pattern)

                if os.path.isdir(pattern):
                    # Nếu là thư mục: đệ quy lấy tất cả file trong đó
                    for root, _, filenames in os.walk(pattern):
                        for fname in filenames:
                            files.append(os.path.join(root, fname))

                elif any(sep in pattern for sep in ('*', '?', '\\', '/')):
                    # Nếu có wildcard hoặc đường dẫn: dùng glob
                    matched = glob.glob(pattern, recursive=True)
                    if matched:
                        for m in matched:
                            if os.path.isdir(m):
                                for root, _, filenames in os.walk(m):
                                    for fname in filenames:
                                        files.append(os.path.join(root, fname))
                            elif os.path.isfile(m):
                                files.append(m)
                    else:
                        print(f"[WARNING] Không tìm thấy file khớp với: {pattern}")

                else:
                    # Kiểm tra nếu là file trong thư mục hiện tại
                    full_path = os.path.join('.', pattern)
                    if os.path.isfile(full_path):
                        files.append(full_path)
                    elif os.path.isdir(full_path):
                        for root, _, filenames in os.walk(full_path):
                            for fname in filenames:
                                files.append(os.path.join(root, fname))
                    else:
                        print(f"[WARNING] Không tìm thấy: {pattern}")

        uploaded = set()

        for filepath in files:
            filepath = os.path.normpath(filepath)
            if filepath in uploaded:
                continue
            uploaded.add(filepath)

            if os.path.isfile(filepath):
                if self.prompt:
                    ans = input(f"Upload {filepath}? (y/n): ")
                    if ans.lower() != 'y':
                        continue
                self.put(filepath)
            else:
                print(f"[ERROR] '{filepath}' không phải là file hợp lệ.")


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
                    data = f.read(4096)
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
  prompt                    Toggle prompt for mget/mput
  ls                        List files on server
  cd <dir>                  Change server directory
  pwd                       Print working directory
  mkdir <name>              Create server directory
  rmdir <name>              Remove server directory
  delete <file>             Delete file on server
  rename <from> <to>        Rename file on server
  get <file>                Download file
  mget <pattern>            Download multiple files
  put <file>                Upload file (scan first)
  mput <pattern>            Upload multiple files (scan all)
  help, ?                   Show this help
  quit, bye                 Exit the client
""")


def main():
    client = FTPClient()
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
                client.connect(parts[1], int(parts[2]) if len(parts) > 2 else 21)
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
                client.cd(parts[1])
            elif cmd == 'pwd':
                client.pwd()
            elif cmd == 'mkdir':
                client.mkdir(parts[1])
            elif cmd == 'rmdir':
                client.rmdir(parts[1])
            elif cmd == 'delete':
                client.delete(parts[1])
            elif cmd == 'rename':
                client.rename(parts[1], parts[2])
            elif cmd in ('get', 'recv'):
                if len(parts) == 2:
                    client.get(parts[1])
                elif len(parts) == 3:
                    client.get(parts[1], parts[2])
                else:
                    print("Usage: get <remote_filename> [local_path]")
            elif cmd == 'mget':
                client.mget(command[len('mget'):].strip())
            elif cmd == 'put':
                client.put(parts[1])
            elif cmd == 'mput':
                client.mput(command[len('mput'):].strip())
            elif cmd in ('help', '?'):
                client.help()
            else:
                print(f"Unknown command: {cmd}")
        except Exception as e:
            print(f"[ERROR] {str(e)}")

if __name__ == '__main__':
    main()
