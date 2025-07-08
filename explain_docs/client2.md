The provided Python code defines an `FTPClient` class that acts as a secure FTP client, allowing users to connect to an FTP server, perform file transfers (upload/download), directory operations, and crucially, it integrates with a ClamAV agent for malware scanning during file uploads.

Here's a breakdown of the file's content:

**1. Imports:**
*   `os`: Provides functions for interacting with the operating system, like path manipulation (`os.path.join`, `os.path.basename`, `os.path.isdir`, `os.path.isfile`) and directory creation (`os.makedirs`).
*   `socket`: Used for low-level network communication, specifically to connect to the ClamAV agent.
*   `ftplib`: The standard Python library for implementing the FTP protocol. `FTP_TLS` is a subclass of `FTP` that adds explicit FTPS (FTP over TLS/SSL) support.
*   `fnmatch`: Provides support for Unix shell-style wildcards (like `*` and `?`) for filename matching. While imported, it's not directly used with `fnmatch.fnmatch()` in the `mget` or `mput` functions; `glob` is used for pattern matching which internally uses `fnmatch`.
*   `glob`: Used for finding pathnames matching a specified pattern, similar to Unix shell globbing, including recursive matching with `**`.

**2. Global Constants:**
*   `CLAMAV_HOST = '127.0.0.1'`: The IP address of the ClamAV agent.
*   `CLAMAV_PORT = 6789`: The port on which the ClamAV agent is listening.

**3. `FTPClient` Class:**

This class encapsulates all the FTP client functionalities.

*   **`__init__(self)`:**
    *   Initializes the `FTP_TLS` object (`self.ftp`) which will be used for FTP communication.
    *   Sets default modes: `passive_mode` (True, common for firewalls), `transfer_mode` (binary), and `prompt` (True, for user confirmation on multiple file operations).

*   **`connect(self, host, port=21)`:**
    *   Establishes a secure FTP connection using `FTP_TLS`.
    *   Prompts the user for username and password.
    *   `self.ftp.connect(host, port)`: Connects to the server.
    *   `self.ftp.auth()`: Initiates TLS/SSL authentication on the control connection.
    *   `self.ftp.login(user=user, passwd=passwd)`: Logs in to the FTP server.
    *   `self.ftp.prot_p()`: Sets the data connection to be protected (private), which is crucial for secure data transfers with FTPS.
    *   `self.ftp.set_pasv(self.passive_mode)`: Configures passive or active mode for data transfers.
    *   Includes error handling for authentication (`error_perm`) and general exceptions.

*   **`disconnect(self)`:**
    *   Gracefully disconnects from the FTP server using `self.ftp.quit()`.

*   **`status(self)`:**
    *   Prints the current client settings (passive mode, transfer mode) and connection status.

*   **`toggle_prompt(self)`, `set_ascii(self)`, `set_binary(self)`, `toggle_passive(self)`:**
    *   Utility methods to change client settings like prompting for `mget`/`mput`, setting ASCII or binary transfer mode, and toggling passive/active FTP mode.

*   **Basic FTP Operations:**
    *   `ls()`: Lists files and directories on the remote server (`LIST` command).
    *   `cd(self, path)`: Changes the current working directory on the server (`CWD` command).
    *   `pwd()`: Prints the current working directory on the server (`PWD` command).
    *   `mkdir(self, dirname)`: Creates a directory on the server (`MKD` command).
    *   `rmdir(self, dirname)`: Removes a directory on the server (`RMD` command).
    *   `delete(self, filename)`: Deletes a file on the server (`DELE` command).
    *   `rename(self, from_name, to_name)`: Renames a file on the server (`RNFR`, `RNTO` commands).

*   **`get(self, filename, destination_path=None)`:**
    *   Downloads a single file from the FTP server.
    *   Handles `destination_path`:
        *   If `destination_path` is a directory, it saves the file with its original basename inside that directory.
        *   Otherwise, `destination_path` is treated as the full local path, including the new filename.
        *   If `destination_path` is `None`, it defaults to saving in the current local directory with the original filename.
    *   Uses `self.ftp.retrbinary(f"RETR {filename}", f.write)` for binary transfer.

*   **`mget(self, args)`:**
    *   Downloads multiple files, supporting wildcards and recursive directory downloads.
    *   Parses arguments to determine file patterns and an optional destination directory.
    *   **`is_directory(name)` helper:** Attempts to `cwd` into a remote item. If successful, it's a directory; otherwise, it's a file or not accessible.
    *   **`recursive_download(remote_path, local_path)` helper:**
        *   Recursively downloads files and subdirectories from `remote_path` on the server to `local_path` locally.
        *   Uses `os.makedirs(local_path, exist_ok=True)` to ensure the local directory exists.
        *   Uses `self.ftp.retrlines(f'LIST {remote_path}', file_list.append)` to get directory listings.
        *   Includes a prompt (`self.prompt`) for user confirmation before downloading each file or directory.
    *   Uses `self.ftp.nlst(pattern)` to get a list of matching filenames from the server for a given pattern.

*   **`put(self, filepath)`:**
    *   Uploads a single file to the FTP server.
    *   **Crucially, it includes a `self.scan_with_clamav(filepath)` call before uploading.**
    *   Only proceeds with upload if the scan result is "OK".
    *   Uses `self.ftp.storlines` for ASCII mode or `self.ftp.storbinary` for binary mode.

*   **`mput(self, args)`:**
    *   Uploads multiple files, supporting wildcards and recursive directory uploads from the local filesystem.
    *   Uses `glob.glob(pattern, recursive=True)` to find local files matching patterns.
    *   Iterates through found files/directories:
        *   If it's a directory, it uses `os.walk` to find all files within it.
        *   If it's a file, it adds it to the list.
    *   Includes a prompt (`self.prompt`) for user confirmation before uploading each file.
    *   Calls `self.put(filepath)` for each file, which means each file will be scanned by ClamAV before upload.

*   **`scan_with_clamav(self, filepath)`:**
    *   This is the security integration point.
    *   It opens a socket connection to a ClamAV agent running at `CLAMAV_HOST:CLAMAV_PORT`.
    *   Sends file metadata (basename and size) to the agent.
    *   Waits for an `META_OK` acknowledgment from the agent.
    *   Sends the file content in chunks (4096 bytes at a time) over the socket.
    *   Receives the scan result ("OK" or "INFECTED") from the ClamAV agent.
    *   Returns the result string or an error message if communication fails.

*   **`help(self)`:**
    *   Prints a list of supported commands for the client, providing a basic command-line interface guide.

**4. `main()` Function:**

*   Creates an instance of `FTPClient`.
*   Enters an infinite loop to act as a command-line interpreter.
*   Takes user input for commands (e.g., `open`, `ls`, `put`, `get`, `quit`).
*   Parses the command and calls the corresponding method of the `FTPClient` object.
*   Includes a general `try-except` block to catch and print any unhandled errors during command execution.

**Overall Purpose:**

This `client2.py` script provides a command-line utility for secure FTP operations, with a significant added security feature: **all files uploaded via the `put` or `mput` commands are first sent to a local ClamAV agent for virus scanning.** This prevents the client from inadvertently uploading infected files to the FTP server. It's a robust example of how to build an interactive network client with integrated security checks.