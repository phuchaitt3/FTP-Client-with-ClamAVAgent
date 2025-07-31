1. Extract .ssh.zip to C:\Users\your_user
2. Open powershell
3. Run: ssh root@146.190.91.115
4. When asked for password, type kabom172 (Hidden password)
5. Run: python3 clamav_agent.py

+. If want to see log of ftp server, open another powershell terminal, run step 3 and 4, then run: 
sudo tail -f /var/log/vsftpd.log
