# 📁 Secure FTP Client with Virus Scanning via ClamAVAgent

## 🚀 Project Description

This project simulates a secure file upload system using the FTP protocol, where each file is scanned for viruses by a ClamAVAgent before being uploaded to the server.

## ⚙️ System Components

- `client.py`: A command-line FTP client supporting standard FTP commands and integrated virus scanning.
- `clamav_agent.py`: A scanning server that receives files via socket, scans them using ClamAV (`clamscan`), and returns results.
- **FTP Server**: FileZilla Server (port 21 by default).

---

## 🧩 Requirements

- Python 3.8 or later
- ClamAV installed and `clamscan` available in the system PATH
- FileZilla FTP Server installed and configured
- No external Python libraries required

---

## 🛠️ How to Run

### 1. Start ClamAVAgent server

```bash
python3 clamav_agent.py
```

### 2. Start the FTP client

```bash
python3 client.py
```

Once launched, **you must use the **``** command first to connect to the FTP server**:

```bash
ftp> open 127.0.0.1 21
Username: <your FTP username>
Password: <your FTP password>
```

### 3. When finished, exit cleanly using:

```bash
ftp> quit
```

---

## 🔧 Supported Commands & Parameters

### ✅ `open <host> [port]`

Connect to the FTP server. **This command must be run before using any other commands.**

### ✅ `quit` / `bye`

Exit the FTP client.

### ✅ `put`

Upload a single file (will be scanned first):

- `put <filename>`
- `put <full_path_to_file>`

### ✅ `mput`

Upload multiple files (each file is scanned before upload):

- `mput <file1> <file2> ...`
- `mput <full_path_file1> <full_path_file2> ...`
- `mput <wildcard_pattern>` (e.g., `mput *.txt`, `mput folder/**/*.py`)

### ✅ `get`

Download a single file from the server:

- `get <filename>` → save in current folder with the original name
- `get <filename> <download_directory>` → save in specified folder with original name
- `get <filename> <new_full_path>` → save to specific path and name

### ✅ `mget`

Download multiple files:

- `mget <file1> <file2> ...`
- `mget <file1> <file2> ... <destination_directory>`

### ✅ `delete <filename>`

Delete a file from the FTP server.

### ✅ `rename <old_name> <new_name>`

Rename a file on the FTP server.

### ✅ `mkdir <directory_name>`

Create a new directory on the FTP server.

### ✅ `rmdir <directory_name>`

Remove a directory on the FTP server.

### ✅ `ls`

List files and directories on the server.

### ✅ `cd <directory_name>`

Change working directory on the server.

**Usage in FileZilla**: To configure a native start path for a specific user:

- In FileZilla Server Interface → Configure → Users → Select your user
- Under **Mounting Points**, click "Add" and choose a folder
- Set a **Virtual Path** starting with a `/` (e.g., `/home`, `/data`)
- That virtual path will be the one you use in the client
- Then in `client.py`, use `cd /your_virtual_path` to navigate

### ✅ `pwd`

Display the current directory on the server.

### ✅ `ascii` / `binary`

Switch between ASCII and binary transfer modes.

- **ASCII Mode**: Transfers text files with automatic newline conversion. It may corrupt binary files (e.g., images).
- **Binary Mode**: Transfers files exactly as they are (recommended for images, documents, etc.).

To verify mode correctness:

- Upload a `.jpg` or `.png` file using `ascii` → file will likely be corrupted.
- Upload the same file using `binary` → image remains intact.

Use `ascii` or `binary` command in client to switch mode.

### ✅ `prompt`

Toggle confirmation prompts for `mput` and `mget`.

### ✅ `passive`

Toggle passive FTP mode.

- **Passive Mode (PASV)**: The **client opens a data connection to the server** using an IP and port returned by the server. Used when the client is behind NAT/firewall.
- **Active Mode (PORT)**: The **client listens for data connection**, and tells the server its IP and port to connect back.

In `client.py`, passive mode:

- Sends `PASV`, extracts server data port, connects to it.

In active mode:

- Client starts a temporary listener socket.
- Sends `PORT <ip,port>` to server.
- Server connects to the client.

Use `passive` command to toggle the current mode.

### ✅ `status`

Display current session status.

### ✅ `help`, `?`

Show help message.

---

## 🛡️ Virus Scanning Workflow

Before uploading a file via `put` or `mput`, it is sent to the ClamAVAgent via socket. The agent runs `clamscan`, then returns one of the following results:

- `OK`: Safe to upload to the FTP server
- `INFECTED`: Upload is aborted
- `ERROR`: Scan failed or communication error

---

## ✅ Recommended Usage Checklist

- Use `open` to connect before using any FTP commands
- Use `quit` to exit properly
- Uploads are only allowed if ClamAVAgent reports the file as clean
- Wildcard upload/download (via `mput` / `mget`) works with confirmation prompts
- Ensure `clamscan` runs properly from terminal

---

## 📆 Additional Notes on Implementation

### Function Descriptions from `client.py`

- `connect()`: Connects to the FTP server and logs in.
- `disconnect()`: Sends `QUIT` and closes control socket.
- `_open_data_connection()`: Opens data socket using passive or active mode.
- `toggle_passive()`: Switches between active/passive FTP.
- `set_ascii()` / `set_binary()`: Switches transfer mode and sends appropriate `TYPE` command.
- `put()`: Scans then uploads a single file. Creates remote directories if needed.
- `mput()`: Uploads multiple files using wildcard or list. Prompts user before upload.
- `get()`: Downloads a single file with proper mode handling.
- `mget()`: Downloads multiple files or folders, supports pattern matching and recursion.
- `cd()`: Sends `CWD` to change remote directory.
- `pwd()`: Sends `PWD` to print current server directory.
- `ls()`: Sends `LIST` and prints listing.
- `mkdir()`, `rmdir()`: Create or delete directories on server.
- `delete()`: Deletes a file.
- `rename()`: Renames a remote file.
- `make_remote_dirs()`: Recursively ensures parent folders exist before `put()`.
- `scan_with_clamav()`: Sends file over socket to ClamAV agent for scanning.

---

## 📌 Notes

- **You must use **``** before any other command**
- **Use **``** or **``** to exit the client gracefully**
- All uploaded files are scanned first — infected files will NOT be uploaded

