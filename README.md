# FTP-Client-with-ClamAVAgent

1. Install ClamAV and create freshclam.conf to run freshclam.exe. Add ClamAV to system path.
2. Run clamav_agent.py and leave the agent terminal open.
3. Open another terminal, run "python3 test_client.py [document_name]". Example: python3 test_client.py safe_document.txt. The sample file safe_document.txt is already in main.
