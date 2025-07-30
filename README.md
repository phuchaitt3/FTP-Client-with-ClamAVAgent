# 📁 Secure FTP Client with Virus Scanning via ClamAVAgent

## 🚀 Project Description

This project simulates a secure file upload system using the FTP protocol, where each file is scanned for viruses by a ClamAVAgent before being uploaded to the server.

## ⚙️ System Components

- `ftp_client.py`: A command-line FTP client supporting standard FTP commands and integrated virus scanning.
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
python ftp_client.py
```

Once launched, **you must use the **``** command first to connect to the FTP server**:

```bash
ftp> open 146.190.91.115 21
Username: sinhvien
Password: 12345678
```

> ✅ If you're testing client and server on the same machine, run:
> ```bash
> ftp> testmode on
> ```
> This will force active mode to use 127.0.0.1 for connections.
>
> ✅ If you're testing across different machines (real network), run:
> ```bash
> ftp> testmode off
> ```
> This lets the client use its actual LAN IP for active mode.

### 3. When finished, exit cleanly using:

```bash
ftp> quit
```

---

## 🔧 Supported Commands & Parameters

### ✅ `open <host> [port]`

Connect to the FTP server. **This command must be run before using any other commands.**

---

### ✅ `put`

Upload a file (will be scanned first by ClamAV):

- `put <file_path>` → Can be just a filename or a path to file (even outside current terminal folder)

---

### ✅ `mput`

Upload multiple files and/or folders:

- `mput <file1> <file2> ...`
- `mput <full_path_file1> <full_path_file2> ...`
- `mput <wildcard_pattern>` (e.g., `mput *.txt`, `mput folder/**/*.py`)
- `mput <file1> <file2> ...`  
- `mput <folder1> <folder2> ...`
- `mput *.txt folderA/*.md`
- ✅ You can mix file/folder names and wildcard patterns together:
  ```
  mput *.jpg docs/ notes/*.md
  ```

Each file is scanned individually before upload.

---

### ✅ `get`

Download a single file from the server:

- `get <remote_filename>` → Save to current local directory
- `get <remote_filename> <local_directory>` → Save using original name inside target folder
- `get <remote_filename> <full_local_path>` → Save with new path and/or name

All modes are supported with optional destination.

---

### ✅ `mget`

Download multiple files or folders:

- `mget <file1> <file2> ...`
- `mget <folder1> <file2> ...`
- `mget *.pdf folderA/*.txt`
- `mget *.jpg target_folder/` → final argument is treated as destination folder if it exists

Supports recursion (e.g., downloading folders and their content), and destination folder can be optionally specified as the last argument.

---

### ✅ Other FTP Commands

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
| Command | Description |
|--------|-------------|
| `delete <filename>` | Delete file from FTP server |
| `rename <old_name> <new_name>` | Rename file |
| `mkdir <dir_name>` | Create folder |
| `rmdir <dir_name>` | Remove folder |
| `ls` | List files on server |
| `cd <dir_name>` | Change server directory |
| `pwd` | Show current directory |
| `ascii` / `binary` | Switch transfer mode |
| `prompt` | Toggle y/n confirmation for `mput` and `mget` |
| `passive` | Toggle passive/active mode |
| `status` | Show connection info |
| `help`, `?` | Show help |

---

## 🛡️ Virus Scanning Workflow

Before uploading any file via `put` or `mput`, it is sent to the ClamAVAgent via socket.

The agent runs `clamscan` and returns:

- `OK` → File is clean and will be uploaded
- `INFECTED` → Upload aborted
- `ERROR` → Scan failed or connection problem

---

## ✅ Recommended Usage Checklist

- ✅ Use `open <host>` before any other command
- ✅ Set `testmode on` if client and server run on same machine (forces IP = 127.0.0.1)
- ✅ Use `testmode off` for LAN or different machines (uses real IP)
- ✅ Files are scanned before upload — infected files are blocked
- ✅ You can use wildcard patterns with `mput` and `mget`
- ✅ Use `prompt` to toggle confirmation for batch operations
- ✅ Use `quit` to exit the client cleanly

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

- **You must use `open` before any other command**
- **Use `quit` or `bye` to exit the client gracefully**
- **All uploaded files are scanned**
- **Active and Passive FTP modes are both supported and switchable at runtime**
