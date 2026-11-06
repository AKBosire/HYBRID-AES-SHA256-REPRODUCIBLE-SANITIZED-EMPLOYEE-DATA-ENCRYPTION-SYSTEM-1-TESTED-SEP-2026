"""Generate a short HTTPS evidence trace without altering experiment result files."""
import concurrent.futures
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
TARGET = "https://127.0.0.1:5000/login"

def send_one(_):
    try:
        response = requests.post(TARGET, data={"email": "capture-only@example.invalid", "password": "fabricated-password"}, headers={"X-Evidence-Capture": "1"}, timeout=5, verify=False)
        return response.status_code
    except requests.RequestException:
        return "failed"

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        outcomes = list(executor.map(send_one, range(250)))
    print(f"Capture-only HTTPS requests completed: {len(outcomes)}")
    print(f"HTTP responses: {sum(value != 'failed' for value in outcomes)}; failures: {outcomes.count('failed')}")
    print("No thesis result files were created or replaced.")
