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

## 🛠 How to Run

### 1. Start ClamAVAgent server

```bash
python clamav_agent.py
```

### 2. Start the FTP client

```bash
python ftp_client.py
```

Once launched, **you must use the `open` command first to connect to the FTP server**:

```bash
ftp> open 127.0.0.1 21
Username: <your FTP username>
Password: <your FTP password>
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

## 📎 Notes

- **You must use `open` before any other command**
- **Use `quit` or `bye` to exit the client gracefully**
- **All uploaded files are scanned**
- **Active and Passive FTP modes are both supported and switchable at runtime**
