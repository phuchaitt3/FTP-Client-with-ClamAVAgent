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

    def _reset_connection(self):
        """Resets the connection object after a fatal error."""
        print("[INFO] Connection was closed or has been lost. Resetting.")
        if self.ftp:
            try:
                # Unilaterally close the connection without sending QUIT
                self.ftp.close()
            except Exception as e:
                # Ignore errors during close, as the connection is likely already dead
                pass
        self.ftp = None

    def connect(self, host, port=21):
        if self.ftp:
            print("An existing connection is active. Please 'close' it first.")
            return
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
        except ftplib.error_perm as e:
            print(f"[AUTH ERROR] {e}")
            self._reset_connection()
        except Exception as e:
            print(f"[ERROR] {e}")
            self._reset_connection()

    def disconnect(self):
        if self.ftp:
            try:
                # Politely ask the server to close the connection
                self.ftp.quit()
                print("Disconnected from server.")
            except Exception as e:
                # If quit fails, the connection is likely already broken
                print(f"[INFO] Quit command failed ({e}), closing connection forcibly.")
                self.ftp.close()
            finally:
                 self.ftp = None
        else:
            print("Not connected.")

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
        if not self.ftp:
            print("Not connected.")
            return
        try:
            self.ftp.retrlines('LIST')
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost: {e}")
            self._reset_connection()

    def cd(self, path):
        if not self.ftp:
            print("Not connected.")
            return
        try:
            self.ftp.cwd(path)
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost: {e}")
            self._reset_connection()

    def pwd(self):
        if not self.ftp:
            print("Not connected.")
            return
        try:
            print(self.ftp.pwd())
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost: {e}")
            self._reset_connection()

    def mkdir(self, dirname):
        if not self.ftp:
            print("Not connected.")
            return
        try:
            self.ftp.mkd(dirname)
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost: {e}")
            self._reset_connection()

    def rmdir(self, dirname):
        if not self.ftp:
            print("Not connected.")
            return
        try:
            self.ftp.rmd(dirname)
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost: {e}")
            self._reset_connection()

    def delete(self, filename):
        if not self.ftp:
            print("Not connected.")
            return
        try:
            self.ftp.delete(filename)
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost: {e}")
            self._reset_connection()

    def rename(self, from_name, to_name):
        if not self.ftp:
            print("Not connected.")
            return
        try:
            self.ftp.rename(from_name, to_name)
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost: {e}")
            self._reset_connection()

    def get(self, filename, destination_path=None):
        if not self.ftp:
            print("Not connected.")
            return
        if destination_path:
            if os.path.isdir(destination_path):
                local_path = os.path.join(destination_path, os.path.basename(filename))
            else:
                local_path = destination_path
        else:
            local_path = os.path.basename(filename)

        try:
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f"RETR {filename}", f.write)
            print(f"Downloaded {filename} -> {local_path}")
        except (ConnectionResetError, BrokenPipeError, ftplib.all_errors) as e:
            print(f"[ERROR] Failed to download {filename}: {str(e)}")
            self._reset_connection()
        except Exception as e:
            print(f"[ERROR] Failed to download {filename}: {str(e)}")

    def mget(self, args):
        """
        Downloads multiple remote files/directories from the server.
        Handles wildcards and recursive directory downloads.
        """
        if not self.ftp:
            print("Not connected.")
            return

        args = args.strip().split()
        if not args:
            print("Usage: mget <remote_pattern_1> [remote_pattern_2 ...] [local_destination_dir]")
            return

        # Determine if the last argument is a local destination directory
        potential_dest = args[-1]
        # A simple check: if it exists locally and is a directory.
        if os.path.isdir(potential_dest):
            dest_dir = os.path.normpath(potential_dest)
            patterns = args[:-1]
            print(f"Files will be downloaded to '{dest_dir}'")
        else:
            dest_dir = "." # Current local directory
            patterns = args
        
        if not patterns:
             print("No remote files or patterns specified.")
             return

        def _is_remote_directory(path):
            """Checks if a path on the FTP server is a directory."""
            if not self.ftp: return False
            current_dir = self.ftp.pwd()
            try:
                self.ftp.cwd(path)
                self.ftp.cwd(current_dir) # If both succeed, it's a directory
                return True
            except ftplib.all_errors:
                return False

        def _recursive_download(remote_path, local_path):
            """Recursively downloads a remote directory."""
            if not self.ftp:
                print("[ERROR] Connection lost. Aborting recursive download.")
                return

            try:
                os.makedirs(local_path, exist_ok=True)
                print(f"Entering directory {remote_path} -> {local_path}")
                
                items = self.ftp.nlst(remote_path)
                
                for item_name in items:
                    # nlst can return full paths, we only want the base name
                    base_name = os.path.basename(item_name)
                    if base_name in ('.', '..'):
                        continue

                    full_remote_path = f"{remote_path}/{base_name}"
                    full_local_path = os.path.join(local_path, base_name)
                    
                    if not self.ftp: # Check connection before each item
                        print("[ERROR] Connection lost. Aborting.")
                        return

                    if _is_remote_directory(full_remote_path):
                        _recursive_download(full_remote_path, full_local_path)
                    else:
                        # It's a file, download it
                        self.get(full_remote_path, full_local_path)

            except (ftplib.all_errors, ConnectionError) as e:
                print(f"[ERROR] Could not process directory {remote_path}: {e}")
                self._reset_connection()
            except Exception as e:
                print(f"[ERROR] An unexpected error occurred in recursive download: {e}")

        # Main loop for processing patterns
        for pattern in patterns:
            if not self.ftp:
                print("[ERROR] Connection lost. Aborting mget operation.")
                break
            try:
                matched_items = self.ftp.nlst(pattern)
                if not matched_items:
                    print(f"[INFO] No remote items found matching pattern: {pattern}")
                    continue
            except ftplib.error_perm as e:
                # This often happens for "550 No files found" which is not a fatal error.
                print(f"[INFO] Server response for '{pattern}': {e}")
                continue
            except (ftplib.all_errors, ConnectionError) as e:
                print(f"[ERROR] Failed to list pattern '{pattern}': {e}")
                self._reset_connection()
                continue # Skip to next pattern

            for item in matched_items:
                if not self.ftp:
                    print("[ERROR] Connection lost. Aborting.")
                    break
                
                # Check if it's a directory or a file
                is_dir = _is_remote_directory(item)
                
                if not self.ftp: # _is_remote_directory could lose connection
                     print("[ERROR] Connection lost. Aborting.")
                     break
                
                if self.prompt:
                    try:
                        prompt_msg = "directory" if is_dir else "file"
                        ans = input(f"Download {prompt_msg} {item}? (y/n): ")
                        if ans.lower() != 'y':
                            continue
                    except (EOFError, KeyboardInterrupt):
                         print("\nDownload cancelled by user.")
                         return
                
                if is_dir:
                    # Target for recursive download is a new dir inside dest_dir
                    local_target_path = os.path.join(dest_dir, os.path.basename(item))
                    _recursive_download(item, local_target_path)
                else:
                    # Target for file download is directly inside dest_dir
                    local_target_path = os.path.join(dest_dir, os.path.basename(item))
                    self.get(item, local_target_path)

    def put(self, filepath):
        if not self.ftp:
            print("Not connected.")
            return
        if not os.path.isfile(filepath):
            print(f"File '{filepath}' does not exist.")
            return

        result = self.scan_with_clamav(filepath)
        if result != "OK":
            if "INFECTED" in result:
                print(f"[WARNING] File '{filepath}' is INFECTED. Upload aborted.")
            else:
                print(f"[ERROR] Scan failed: {result}")
            return
        
        try:
            with open(filepath, 'rb') as f:
                if self.transfer_mode == 'ascii':
                    self.ftp.storlines(f"STOR {os.path.basename(filepath)}", f)
                else:
                    self.ftp.storbinary(f"STOR {os.path.basename(filepath)}", f)
            print(f"Uploaded {filepath}")
        except (ConnectionResetError, BrokenPipeError, *ftplib.all_errors) as e:
            print(f"[ERROR] Connection lost during upload: {e}")
            self._reset_connection() # Reset the connection so we can quit cleanly
        except Exception as e:
            print(f"[ERROR] Failed to upload {filepath}: {e}")

    def mput(self, args):
        """
        Uploads multiple local files to the server.
        Handles wildcards and recursive directory uploads.
        """
        if not self.ftp:
            print("Not connected.")
            return
        
        import glob

        args = args.strip()
        if not args:
            print("Usage: mput <file_or_pattern_1> [file_or_pattern_2 ...]")
            print("Example: mput file.txt *.zip my_directory")
            return

        files_to_upload = set() # Use a set to avoid uploading the same file twice
        patterns = args.split()

        for pattern in patterns:
            # Check if the pattern is a directory
            if os.path.isdir(pattern):
                # Walk through the directory and add all files
                for root, _, filenames in os.walk(pattern):
                    for filename in filenames:
                        files_to_upload.add(os.path.join(root, filename))
            else:
                # Use glob to handle wildcards and regular files
                matched_files = glob.glob(pattern, recursive=True)
                if not matched_files:
                    print(f"[WARNING] No local files found matching pattern: {pattern}")
                for f in matched_files:
                    if os.path.isfile(f): # Ensure we only add files, not dirs from glob
                         files_to_upload.add(f)

        if not files_to_upload:
            print("No valid files to upload.")
            return

        print(f"Found {len(files_to_upload)} file(s) to upload.")
        
        for filepath in sorted(list(files_to_upload)):
            if self.prompt:
                try:
                    ans = input(f"Upload {filepath}? (y/n): ")
                    if ans.lower() != 'y':
                        continue
                except (EOFError, KeyboardInterrupt):
                    print("\nUpload cancelled by user.")
                    return

            # Use the robust `put` method for the actual upload and scan
            self.put(filepath)

            # If the connection was lost during the last 'put' operation, stop.
            if not self.ftp:
                print("[ERROR] Connection lost. Aborting mput operation.")
                break

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
        except IndexError:
            print("Invalid command syntax.")
        except Exception as e:
            # General fallback for any other unexpected errors
            print(f"[CRITICAL ERROR] An unexpected error occurred: {e}")
            if client.ftp:
                client._reset_connection()

if __name__ == '__main__':
    main()
