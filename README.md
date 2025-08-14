# 📁 Secure FTP Client with Virus Scanning via ClamAV Agent

## 🚀 Project Description

This project simulates a secure file upload system using the FTP protocol, where each file is scanned for viruses by a ClamAV Agent before being uploaded to the FTP server.

## ⚙️ Main System Components

-   `ftp_client.py`: A command-line FTP client supporting standard FTP commands.
-   `clamav_agent.py`: A scanning server that receives files via socket from the FTP client, scans them using ClamAV (`clamscan`), and returns results.
-   `vsftpd`: FTP Server on Linux OS.
-   Simulate 3 machines with different ports/IPs: `ftp_client.py` runs on the client machine and connects through the Internet to a separate DigitalOcean Droplet (virtual machine) that runs both `clamav_agent.py` and `vsftpd`.

## 🛠️ Configuration Files
-   `config.ini`: Configuration file for the ClamAV agent, specifying the host and port.
-   `.ssh.zip`: Contains SSH keys for secure access to the server.

---

## 🧩 Requirements

-   Python 3.8 or later
-   A configured FTP server (see the setup guide below)
-   ClamAV installed on the Droplet
-   No external Python libraries are required for the client

---

## 🛠️ Server Setup Guide (DigitalOcean)

This section details how to set up a `vsftpd` FTP server and the ClamAV agent on a DigitalOcean Droplet.

### Step 1: Create a DigitalOcean Droplet

1.  **Log in to DigitalOcean.** (Use a GitHub Student account for free credits if available).
2.  Click **Create** in the top-right corner and select **Droplets**.
3.  **Choose the following configuration:**
    *   **Region:** Singapore
    *   **Operating System:** Ubuntu 22.04 x64 (or newer)
    *   **Plan:** Choose a basic plan. This guide was tested on a **$12/month** Droplet, which is sufficient to run the FTP server and ClamAV agent.
    *   **Authentication:** Select **SSH Key**.

4.  **Create and Add a New SSH Key:**
    *   If you don't have an SSH key, open a terminal on your local machine and run:
        ```bash
        ssh-keygen
        ```
    *   Press **Enter** to accept the default file location (`~/.ssh/id_ed25519`).
    *   Enter a secure **passphrase** when prompted. You will need this to connect to your Droplet.
    *   Two files will be created: `id_ed25519` (private key) and `id_ed25519.pub` (public key).
    *   Open the `.pub` file with a text editor and copy its entire content.
    *   Back in DigitalOcean web, click **New SSH Key**, paste the content into the **SSH Key Content** box, give it a name, and add it.

5.  **Finalize Droplet Creation:**
    *   Select the SSH key you just added.
    *   Create a new Project to contain the Droplet.
    *   Click **Create Droplet**.

### Step 2: Configure the Droplet

1.  **Connect to the Droplet via SSH:**
    *   Find your Droplet's public **IPv4 address** from the dashboard.
    *   Open PowerShell (Windows) or Terminal (macOS/Linux) and run:
        ```bash
        ssh root@<YOUR_DROPLET_IPV4>
        ```
    *   Enter the passphrase you created for your SSH key when prompted.

2.  **Update System Packages:**
    ```bash
    sudo apt update
    sudo apt upgrade -y
    ```

3.  **Install Required Software:**
    *   We will install `vsftpd` (a secure FTP server), ClamAV (the antivirus), and Python.
    ```bash
    sudo apt-get install -y vsftpd clamav clamav-daemon python3
    ```

4.  **Configure the Firewall (UFW):**
    *   These rules allow traffic for SSH, FTP, and our ClamAV agent.
    ```bash
    # Allow SSH connections
    sudo ufw allow OpenSSH

    # Allow FTP control port
    sudo ufw allow 21/tcp

    # Allow FTP passive mode port range
    sudo ufw allow 50000:51000/tcp

    # Allow the ClamAV agent port
    sudo ufw allow 6789/tcp
    ```
    *   Enable the firewall and check its status:
    ```bash
    sudo ufw enable
    sudo ufw status
    ```

5.  **Configure the `vsftpd` Server:**
    *   Open the configuration file:
        ```bash
        sudo nano /etc/vsftpd.conf
        ```
    *   Use `Ctrl+W` to search for and ensure the following lines are set (uncomment them or add them if they don't exist):
        ```ini
        anonymous_enable=NO
        local_enable=YES
        write_enable=YES
        chroot_local_user=YES
        ```
    *   Add the following lines to the end of the file for passive mode. **Replace `<YOUR_DROPLET_IPV4>` with your Droplet's actual IP address.**
        ```ini
        pasv_min_port=50000
        pasv_max_port=51000
        pasv_address=<YOUR_DROPLET_IPV4>
        ```
    *   Save and exit the file (`Ctrl+X`, then `Y`, then `Enter`).

6.  **Create an FTP User:**
    *   This command creates a new user named `sinhvien`.
    ```bash
    sudo adduser sinhvien
    ```
    *   You will be prompted to create a password (e.g., `12345678`) and can press Enter to skip the other informational fields.

7.  **Set Up the FTP Directory Structure:**
    *   For security, `vsftpd` requires the user's home directory to be non-writable when `chroot` is enabled. We will create a writable `ftp` subdirectory inside it.
    ```bash
    sudo chmod a-w /home/sinhvien
    sudo mkdir /home/sinhvien/ftp
    sudo chown sinhvien:sinhvien /home/sinhvien/ftp
    ```

8.  **Restart the FTP Server:**
    *   Apply the configuration changes by restarting the `vsftpd` service.
    ```bash
    sudo systemctl restart vsftpd
    ```

9.  **Set Up ClamAV:**
    *   Download the latest virus definitions:
    ```bash
    sudo freshclam
    ```
    *   Create the agent script file on the Droplet:
    ```bash
    nano clamav_agent.py
    ```
    *   Copy the code from the `clamav_agent.py` file in this repository and paste it into the nano editor. Save and exit (`Ctrl+X`, `Y`, `Enter`).

Your server is now configured and ready! The final step is to run the ClamAV agent.

---

## 🛠️ How to Run

### 1. Start ClamAV Agent Server (on the Droplet)

Connect to your Droplet via SSH and run the agent. It needs to be running to handle scan requests from the client.

```bash
python3 clamav_agent.py
```
> **Note:** For long-term use, you should run this script in the background using a tool like `screen` or `tmux` so it doesn't stop when you close your SSH session.

### 2. Start the FTP Client (on your local machine)

```bash
python ftp_client.py
```

Once launched, **you must use the `open` command first to connect to the FTP server**:

```bash
ftp> open <YOUR_DROPLET_IPV4> 21
Username: sinhvien
Password: <your_ftp_user_password>
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

-   `put <file_path>` → Can be just a filename or a path to file (even outside current terminal folder)

---

### ✅ `mput`

Upload multiple files and/or folders:

-   `mput <file1> <file2> ...`
-   `mput <full_path_file1> <full_path_file2> ...`
-   `mput <wildcard_pattern>` (e.g., `mput *.txt`, `mput folder/**/*.py`)
-   `mput <file1> <file2> ...`
-   `mput <folder1> <folder2> ...`
-   `mput *.txt folderA/*.md`
-   ✅ You can mix file/folder names and wildcard patterns together:
    ```
    mput *.jpg docs/ notes/*.md
    ```

Each file is scanned individually before upload.

---

### ✅ `get`

Download a single file from the server:

-   `get <remote_filename>` → Save to current local directory
-   `get <remote_filename> <local_directory>` → Save using original name inside target folder
-   `get <remote_filename> <full_local_path>` → Save with new path and/or name

All modes are supported with optional destination.

**Example:**

If you run:

```bash
ftp> get safe_document.txt D:\TestSocket 

After download completes, the client will display extra information including:

[DEBUG] EPSV response: 229 Entering Extended Passive Mode (|||50515|)
226 Transfer complete.
Downloaded safe_document.txt --> D:\TestSocket\safe_document.txt


---

### ✅ `mget`

Download multiple files or folders:

-   `mget <file1> <file2> ...`
-   `mget <folder1> <file2> ...`
-   `mget *.pdf folderA/*.txt`
-   `mget *.jpg target_folder/` → final argument is treated as destination folder if it exists

Supports recursion (e.g., downloading folders and their content), and destination folder can be optionally specified as the last argument.

---

### ✅ Other FTP Commands

| Command                        | Description                                          |
| ------------------------------ | ---------------------------------------------------- |
| `delete <filename>`            | Delete file from FTP server                          |
| `rename <old_name> <new_name>` | Rename file                                          |
| `mkdir <dir_name>`             | Create folder                                        |
| `rmdir <dir_name>`             | Remove folder                                        |
| `ls`                           | List files on server                                 |
| `cd <dir_name>`                | Change server directory                              |
| `pwd`                          | Show current directory                               |
| `ascii` / `binary`             | Switch transfer mode                                 |
| `prompt`                       | Toggle y/n confirmation for `mput` and `mget`        |
| `passive`                      | Toggle passive/active mode                           |
| `status`                       | Show connection info                                 |
| `help`, `?`                    | Show help                                            |

---

### Command Details

-   **`cd <directory_name>`**: On the `vsftpd` server we configured, your starting directory will be `/`. This corresponds to `/home/sinhvien` on the server's filesystem. The writable directory is `ftp`. So, after logging in, you should run `cd ftp` to upload files.
-   **`ascii` / `binary`**: Switch between ASCII (for text) and binary (for all other files) transfer modes. Binary is the default and recommended for most uses.
-   **`passive`**: Toggles between passive and active FTP modes. Passive mode is generally required when the client is behind a firewall or NAT, which is the most common scenario.

---

## 🛡️ Virus Scanning Workflow

Before uploading any file via `put` or `mput`, it is sent to the ClamAV Agent via a socket connection.

The agent runs `clamscan` and returns:

-   `OK` → File is clean and will be uploaded.
-   `INFECTED` → The file is infected, and the upload is aborted.
-   `ERROR` → The scan failed, and the upload is aborted.

---

## ✅ Recommended Usage Checklist

-   ✅ Follow the server setup guide to prepare your DigitalOcean Droplet.
-   ✅ Start the `clamav_agent.py` script on the server before running the client.
-   ✅ Use `open <host>` in the client before any other command.
-   ✅ Use `cd ftp` after logging in to navigate to the writable directory.
-   ✅ Files are scanned before upload — infected files are blocked.
-   ✅ Use wildcard patterns with `mput` and `mget` for batch operations.
-   ✅ Use `quit` or `bye` to exit the client cleanly.

---

## 📌 Implementation Notes

-   **You must use `open` before any other command.**
-   **All uploaded files are scanned by the agent on the server.**
-   **Active and Passive FTP modes are both supported and switchable at runtime.**