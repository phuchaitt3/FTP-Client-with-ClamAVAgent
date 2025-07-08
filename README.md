
# 📁 Secure FTP Client with Virus Scanning via ClamAVAgent

## 🚀 Project Description

This project simulates a secure file upload system using the FTP protocol, where each file is scanned for viruses by a ClamAVAgent before being uploaded to the server.

## ⚙️ System Components

- `client2.py`: A command-line FTP client supporting standard FTP commands and integrated virus scanning.
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

### 2. Start the FTP client **on another terminal**

```bash
python client2.py
```

Once launched, **you must use the `open` command first to connect to the FTP server**:

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

### ✅ `pwd`

Display the current directory on the server.

### ✅ `ascii` / `binary`

Switch between ASCII and binary transfer modes.

### ✅ `prompt`

Toggle confirmation prompts for `mput` and `mget`.

### ✅ `passive`

Toggle passive FTP mode.

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

## 📎 Notes

- **You must use `open` before any other command**
- **Use `quit` or `bye` to exit the client gracefully**
- All uploaded files are scanned first — infected files will NOT be uploaded
