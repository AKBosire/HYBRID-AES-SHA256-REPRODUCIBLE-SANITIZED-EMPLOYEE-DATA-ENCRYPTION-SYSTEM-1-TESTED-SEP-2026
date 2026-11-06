# Corrected Reproducible Experimental Prototype

This package is a sanitized research copy of the Employee Data Management prototype. It contains no database, Fernet key, TLS private key, email password, personal photograph or experimental result. All output files must be generated on the researcher's test laptop.

## What was corrected

- Removed generated AES, SHA-256 and attack-intensity values.
- Removed randomness from workload detection.
- Separated Fernet benchmarks from login-load measurements.
- Added actual request timing, status, failure and timeout collection.
- Added actual server-side SHA-256 and request-processing timing.
- Added five declared workload levels with three repetitions each.
- Added deterministic synthetic employee-record generation.
- Removed email transmission and all embedded credentials.
- Added local-only HTTP and HTTPS comparison applications.

The workload is a controlled concurrent-login stress simulation. It is not an internet-scale distributed denial-of-service attack or a DDoS mitigation appliance.

## Windows setup

Open Command Prompt in this folder and run:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

Create the 50 fixed synthetic records:

```bat
py generate_synthetic_records.py
```

Generate a self-signed certificate with an installed OpenSSL executable:

```bat
openssl req -x509 -newkey rsa:2048 -nodes -keyout data\key.pem -out data\cert.pem -days 365 -subj "/C=KE/ST=Kajiado/L=Ngong/O=JKUAT-Research/CN=127.0.0.1"
```

The browser will warn that the certificate is self-signed. That is expected in this isolated laboratory test.

## Start the protected application

In the first Command Prompt window:

```bat
.venv\Scripts\activate
py app.py
```

Verify `https://127.0.0.1:5000/health` before starting a workload. Keep the application running.

## Run the genuine cryptographic benchmark

In a second Command Prompt window:

```bat
.venv\Scripts\activate
py crypto_benchmark.py --iterations 1000
```

The raw CSV contains every measured Fernet encryption, Fernet decryption and SHA-256 operation. The JSON summary contains calculated means and the number of verified encryption-decryption round trips.

## Run the controlled login workload suite

While the protected application remains running:

```bat
py workload_experiment.py --suite
```

The suite performs each of these levels three times:

| Level | Total requests | Concurrent workers |
|---|---:|---:|
| Baseline | 100 | 1 |
| Low | 250 | 10 |
| Moderate | 500 | 25 |
| High | 1000 | 50 |
| Stress | 1000 | 100 |

Each raw CSV records request index, timestamp, HTTP status, outcome, error type and actual response time. Each summary JSON reports duration, completion/failure percentages, throughput, mean, median, 95th-percentile, minimum and maximum response time. `experiment_manifest.json` identifies all 15 runs. The server separately writes actual SHA-256 time, total login-processing time, observed request rate and deterministic alert status to `results/server_login_metrics.csv`.

Do not close the server or run unrelated heavy applications during the suite. Record the laptop processor, RAM, Windows version and installed package versions.

```bat
py --version
py -m pip freeze > results\installed_packages.txt
systeminfo > results\windows_system_information.txt
```

## Wireshark comparison

For secure traffic, capture the loopback interface while using the protected application. Suggested filters:

```text
tcp.port == 5000
tcp.port == 5000 && tls
tcp.port == 5000 && tls.handshake
tcp.port == 5000 && tls.app_data
```

For the intentionally insecure local comparison, run:

```bat
py insecure_http_demo.py
```

Open `http://127.0.0.1:5001`, submit only the fabricated values supplied in the form, and filter Wireshark with `tcp.port == 5001`. Stop the demonstration immediately after capture. Never bind it to a public interface.

## Research evidence to retain

Retain the following together without editing raw values:

1. All raw CSV files.
2. All JSON summaries and the experiment manifest.
3. `server_login_metrics.csv`.
4. Installed package and Windows system information files.
5. Wireshark capture files and screenshots.
6. A dated experiment log recording start time, test operator and any interruption.

Do not commit the `data` directory contents, `results` files or uploads to a public repository. The `.gitignore` prevents accidental inclusion.

## Important interpretation boundaries

- Fernet is the high-level authenticated-encryption API used by the implementation. Do not label measured Fernet operations as a newly invented cipher.
- Unsalted SHA-256 is retained for approved prototype comparison only and is not recommended for production password storage.
- A rejected login that receives an HTTP response is a completed request, not an authenticated login.
- The alert is a deterministic threshold rule, not a trained DDoS classifier.
- Local stress-test findings do not establish commercial-cloud or internet-scale DDoS capacity.
