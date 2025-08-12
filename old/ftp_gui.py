
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from ftp_client import FTPClient


class FTPGuiApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Secure FTP Client with ClamAV")
        self.master.geometry("600x400")
        self.client = FTPClient()

        # Top Frame: Connection Controls
        top_frame = tk.Frame(master)
        top_frame.pack(pady=5)

        self.host_entry = tk.Entry(top_frame, width=20)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(side=tk.LEFT, padx=5)

        self.port_entry = tk.Entry(top_frame, width=5)
        self.port_entry.insert(0, "21")
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.connect_btn = tk.Button(top_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(master, orient="horizontal", length=580, mode="determinate")
        self.progress.pack(pady=10)

        # Upload Button
        self.upload_btn = tk.Button(master, text="Upload File", command=self.select_and_upload_file, state=tk.DISABLED)
        self.upload_btn.pack(pady=5)

        # Log area
        self.log_text = tk.Text(master, height=10, width=70)
        self.log_text.pack(padx=10, pady=10)
        self.log("Application started. Please connect to FTP server.")

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def connect_to_server(self):
        host = self.host_entry.get()
        port = int(self.port_entry.get())

        try:
            self.client.connect(host, port)
            self.log(f"Connected to FTP server at {host}:{port}")

            # Login prompt
            username = tk.simpledialog.askstring("Username", "Enter FTP username:")
            password = tk.simpledialog.askstring("Password", "Enter FTP password:", show='*')
            self.client.ftp.login(user=username, passwd=password)

            self.upload_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Connection", "Successfully connected and logged in.")
            self.log("FTP login successful.")
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            self.log(f"[ERROR] Connection failed: {e}")

    def select_and_upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        # Use thread to avoid GUI freeze during upload
        threading.Thread(target=self.upload_file_with_progress, args=(file_path,)).start()

    def upload_file_with_progress(self, file_path):
        import os

        try:
            file_size = os.path.getsize(file_path)
            sent_bytes = 0

            self.log(f"Scanning file: {file_path}")
            scan_result = self.client.scan_with_clamav(file_path)
            self.log(f"Scan result: {scan_result}")

            if scan_result == "OK":
                with open(file_path, 'rb') as f:
                    filename = os.path.basename(file_path)
                    if self.client.transfer_mode == 'ascii':
                        self.client.ftp.storlines(f"STOR {filename}", f)
                    else:
                        def callback(data):
                            nonlocal sent_bytes
                            sent_bytes += len(data)
                            self.progress["value"] = (sent_bytes / file_size) * 100
                            self.master.update_idletasks()

                        self.progress["maximum"] = 100
                        self.progress["value"] = 0
                        self.client.ftp.storbinary(f"STOR {filename}", f, 4096, callback)

                messagebox.showinfo("Upload Complete", f"Uploaded: {file_path}")
                self.log(f"Upload complete: {file_path}")

            elif scan_result == "INFECTED":
                messagebox.showwarning("Virus Detected", "The file is infected and was not uploaded.")
                self.log("Upload aborted: File is infected.")
            else:
                messagebox.showerror("Scan Error", scan_result)
                self.log(f"[ERROR] Scan failed: {scan_result}")

        except Exception as e:
            messagebox.showerror("Upload Failed", str(e))
            self.log(f"[ERROR] Upload failed: {e}")

        self.progress["value"] = 0


if __name__ == "__main__":
    root = tk.Tk()
    app = FTPGuiApp(root)
    root.mainloop()
