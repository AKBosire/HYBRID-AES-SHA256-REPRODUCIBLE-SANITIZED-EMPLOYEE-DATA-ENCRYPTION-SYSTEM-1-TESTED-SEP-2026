# Controlled Experimental Protocol

## Purpose

The protocol evaluates four distinct properties without combining unlike measurements: protection of selected database fields at rest, SHA-256 credential transformation, TLS protection in transit, and application behaviour during controlled concurrent-login workloads.

## Fixed conditions

- Run every workload level on the same laptop and power setting.
- Close unrelated resource-intensive programs.
- Use the same Python environment and application version for all runs.
- Use 50 deterministic fabricated employee records.
- Use the same invalid fabricated credential in all workload requests.
- Use a 1.2-second client timeout.
- Perform three repetitions at each workload level.
- Do not edit raw CSV or JSON output.
- Record any interrupted or abnormal run and repeat it rather than silently deleting it.

## Independent variable

The controlled independent variable is concurrent worker count: 1, 10, 25, 50 and 100. Total requests are 100, 250, 500, 1,000 and 1,000 respectively.

## Dependent measurements

- Completed and failed requests
- Failure and completion percentages
- Actual elapsed duration
- Achieved completed requests per second
- Mean, median, minimum, maximum and 95th-percentile response time
- Server-side SHA-256 duration
- Total server-side login processing duration
- Observed one-second request rate
- Deterministic threshold-alert status
- Fernet encryption and decryption duration in a separate benchmark
- Successful Fernet round trip and rejection of modified tokens

## Controls

The baseline uses one worker. Target URL, submitted credentials, timeout, application code, database, TLS configuration, hardware and software versions remain fixed across workload levels.

## Interpretation

A completed HTTP response to an invalid credential shows that the server handled the request; it does not mean authentication succeeded. An alert shows that the declared threshold was crossed; it is not classifier accuracy. Local workload results characterize this prototype and laptop only and do not establish internet-scale DDoS resistance.
