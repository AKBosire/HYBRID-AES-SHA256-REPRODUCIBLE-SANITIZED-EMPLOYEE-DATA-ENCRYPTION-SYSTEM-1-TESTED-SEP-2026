AUTOMATED 50-RECORD INSECURE DEMONSTRATION UPDATE

1. Stop insecure_http_demo.py with CTRL+C if it is running.
2. Copy the supplied insecure_http_demo.py into HYBRID-AES-SHA256-CORRECTED.
3. Choose "Replace the file in the destination" when Windows asks.
4. Activate the environment and run: py insecure_http_demo.py
   The disposable insecure comparison database is automatically reset to
   exactly 50 fixed, fictional company records every time this script starts.
5. Start Wireshark on the loopback adapter and apply: tcp.port == 5001
6. Open http://127.0.0.1:5001/database to view the 50 fictional records.
7. Open http://127.0.0.1:5001 and submit fabricated record 50 once.
8. Stop capture and apply: tcp.port == 5001 && http.request.method == "POST"
9. Select the POST packet. In the lower-left pane expand:
   Hypertext Transfer Protocol > HTML Form URL Encoded

The fabricated employee fields will appear individually. All names are visibly
marked [Fictional], emails use example.invalid, and displayed passwords are
demonstration strings. Never replace them with real personal information.
This update does not modify the secure database or experiment results.
