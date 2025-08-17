# clamav_agent.py
import socket
import subprocess
import os

# --- Configuration ---
# "Nếu có bất kỳ kết nối nào đến cổng 6789 trên bất kỳ địa chỉ IP nào của máy này (Droplet), hãy chuyển kết nối đó cho tôi."
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 6789         # Port to listen on
TEMP_DIR = "temp_scans"

def setup_environment():
    """Create the temporary directory for file scans if it doesn't exist."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        print(f"Created temporary scan directory: {TEMP_DIR}")

def scan_file(file_path):
    """
    Scans a file using the real clamscan command and checks its exit code.
    """
    # Ensure the file exists before scanning
    if not os.path.exists(file_path):
        print(f"ERROR: File does not exist at path: {file_path}")
        return "ERROR: File not found for scanning"
    
    try:
        # clamscan là executable program, một phần của bộ công cụ chống virus ClamAV, được cài đặt trên hệ điều hành của máy
        # Cần một cách để chạy chương trình đó từ bên ngoài và tương tác với nó: Module subprocess của Python
        result = subprocess.run(
            # '--no-summary': không in ra bản tóm tắt kết quả
            # User chỉ quan tâm OK hay INJECTED
            ['clamscan', '--no-summary', file_path],
            # True: Save stdout và stderr của clamscan vào result. Nếu cần debug
            capture_output=True,
            # Save đưới dạng string (False thì byte)
            text=True
        )

        # Check the return code from clamscan
        if result.returncode == 0:
            return "OK"
        # Virus found
        elif result.returncode == 1:
            return "INFECTED"
        # Any other non-zero return code is an error
        else:
            print(f"ERROR: Clamscan failed with error code {result.returncode} for file {file_path}.")
            print(f"ERROR: Clamscan stderr: {result.stderr.strip()}")
            return "ERROR: Scan failed"

    except FileNotFoundError:
        print("ERROR: `clamscan` command not found. Please ensure ClamAV is installed and in your system's PATH.")
        return "ERROR: clamscan not found"
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during scan: {e}")
        return f"ERROR: {e}"
    
def handle_client(conn, addr):
    """Handle a single client connection."""
    try:
        # 1. Receive file metadata (filename and filesize) sent by client
        metadata = conn.recv(1024).decode()
        if not metadata:
            print(f"ERROR: Client {addr} connected but sent no data.")
            return

        filename, filesize_str = metadata.split(':')
        filesize = int(filesize_str)

        # Send acknowledgment to start file transfer
        conn.sendall(b"META_OK")

        # 2. Receive file data
        # Create a temporary file in the TEMP_DIR for scanning
        temp_file_path = os.path.join(TEMP_DIR, os.path.basename(filename))
        # Write binary
        with open(temp_file_path, 'wb') as f:
            received_bytes = 0
            while received_bytes < filesize:
                # Đọc tối đa 4096 byte (BUFFER_SIZE) từ socket trong mỗi lần gọi
                data = conn.recv(4096)
                # Kiểm tra nếu `data` rỗng có nghĩa là kết nối đã bị đóng đột ngột từ phía client.
                if not data:
                    break
                # Write data vào temp file
                f.write(data)
                received_bytes += len(data)
        
        # Check xem đã nhận đầy đủ file
        if received_bytes == filesize:
            # 3. Scan the temporary file
            # Nếu temp file an toàn thì file của client cũng an toàn và có thể up lên FTP server
            # - Tính toàn vẹn của dữ liệu: Bạn phải đảm bảo rằng quá trình truyền file từ client đến ClamAV agent không làm hỏng dữ liệu. 
            # Việc sử dụng TCP/IP (socket.SOCK_STREAM) đã cung cấp độ tin cậy cao về tính toàn vẹn.
            # - File gốc trên client không bị thay đổi hoặc nhiễm virus giữa thời điểm quét và thời điểm tải lên FTP server. 
            # Trong hầu hết các trường hợp, khoảng thời gian này là rất ngắn.
            scan_result = scan_file(temp_file_path)

            # 4. Send result back to client
            # encode(): Chuyển đổi result thành byte để gửi, bên client sẽ decode thành string
            conn.sendall(scan_result.encode())
        else:
            print(f"ERROR: File transfer incomplete for '{filename}'. Expected {filesize}, got {received_bytes}")
            conn.sendall(b"ERROR: Incomplete file transfer")

    except Exception as e:
        print(f"ERROR: An error occurred with client {addr}: {e}")
    finally:
        # 5. Cleanup
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        conn.close()
        
def main():
    """Main function to run the ClamAV agent server."""
    # Create temp_scans directory
    setup_environment()
    print(f"ClamAV Agent listening on {HOST}:{PORT}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        # Lắng nghe trên 0.0.0.0 6789
        s.listen()

        while True:
            try:
                # Chương trình sẽ bị chặn đến khi một client thực hiện một yêu cầu kết nối thành công.
                # Improvement: Sử dụng threading để xử lý nhiều client cùng lúc
                conn, addr = s.accept()
                handle_client(conn, addr)
            except KeyboardInterrupt:
                print("\nServer is shutting down.")
                break
            except Exception as e:
                print(f"ERROR: Main loop error: {e}")

if __name__ == "__main__":
    main()