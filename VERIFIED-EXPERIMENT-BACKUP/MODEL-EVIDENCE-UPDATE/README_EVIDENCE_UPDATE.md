# Evidence update

This update adds protected administrator evidence views, a plaintext local comparison database, and a capture-only HTTPS traffic generator. It does not replace or edit the verified 15-run experiment results.

1. Copy the update files into the corrected project, preserving the `templates` folder.
2. With the virtual environment active, run `py setup_admin.py`.
3. Restart the protected server with `py app.py`.
4. Visit `https://127.0.0.1:5000/admin/encrypted`; it must redirect to the administrator login.
5. After login, capture the encrypted and authorized decrypted views, then log out.
6. In another terminal run `py insecure_http_demo.py`, open `http://127.0.0.1:5001`, submit only the supplied fabricated values, and capture `/database`.
7. Stop the insecure demo immediately after evidence capture.

Do not publish `data/admin_password.hash`, either database, the Fernet key, TLS private key, or experiment result files.
