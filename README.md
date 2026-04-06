# Owl Detection Report & Benchmark Generator

Automated daily comparison of [Owl Browser](https://owlbrowser.net) vs vanilla Playwright and Puppeteer on [CreepJS](https://abrahamjuliot.github.io/creepjs/) — the industry-standard fingerprint detection tool. Also includes a performance benchmark mode.

Results are displayed at [owlbrowser.net/detection-test](https://owlbrowser.net/detection-test).

## What this generates

### Detection Report (default)
Screenshots and parsed fingerprint data showing:
- **Playwright & Puppeteer** have identical fingerprint hashes (canvas, WebGL, audio, fonts) — they leak the real device
- **Owl Browser** has completely different hashes per OS profile — genuine C++ source-level spoofing
- Headless detection: Playwright `100%`, Puppeteer `100%`, Owl Browser `0%`
- GPU: Playwright/Puppeteer expose SwiftShader (dead giveaway), Owl shows real GPU profiles

### Performance Benchmark (`--benchmark`)
Times cold start, navigation, screenshot, and full cycle for all three browsers:
- 10 sequential iterations per browser
- Statistics: min, max, avg, median, p95
- Raw timing data included for reproducibility
- Same machine, same container, same network — fair comparison

## Quick Start

### 1. Pull the image

```bash
docker pull ghcr.io/olib-ai/owl-detection-report:latest
```

### 2. Create your `.env` file

```bash
cp .env.example .env
# Edit with your values
```

```env
OWL_BROWSER_URL=http://your-owl-instance:8080
OWL_BROWSER_TOKEN=your-token

# Optional — S3 upload
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET=your-bucket
S3_PREFIX=detection-reports
```

### 3. Run detection report

```bash
docker run --rm \
  --network host \
  --env-file .env \
  -v $(pwd)/output:/output \
  ghcr.io/olib-ai/owl-detection-report:latest
```

### 4. Run benchmark

```bash
docker run --rm \
  --network host \
  --env-file .env \
  -v $(pwd)/output:/output \
  ghcr.io/olib-ai/owl-detection-report:latest --benchmark
```

### 5. Set up daily cron

```bash
crontab -e
```

```cron
# Detection report — daily at 3am UTC
0 3 * * * docker run --rm --network host --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest >> /var/log/owl-report.log 2>&1

# Benchmark — weekly on Sunday at 4am UTC
0 4 * * 0 docker run --rm --network host --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest --benchmark >> /var/log/owl-benchmark.log 2>&1
```

> When using S3 upload, the `-v` volume mount is optional since files go directly to S3.

## Build from source

```bash
git clone https://github.com/Olib-AI/owl-detection-report.git
cd owl-detection-report
docker build -t owl-detection-report .

# Detection report
docker run --rm --network host --env-file .env -v $(pwd)/output:/output owl-detection-report

# Benchmark
docker run --rm --network host --env-file .env -v $(pwd)/output:/output owl-detection-report --benchmark
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OWL_BROWSER_URL` | Yes | — | Owl Browser REST API endpoint (e.g. `http://localhost:8080`) |
| `OWL_BROWSER_TOKEN` | Yes | — | Owl Browser API token |
| `OUTPUT_DIR` | No | `/output` | Output directory inside the container |
| `AWS_ACCESS_KEY_ID` | No | — | AWS credentials for S3 upload |
| `AWS_SECRET_ACCESS_KEY` | No | — | AWS credentials for S3 upload |
| `S3_BUCKET` | No | — | S3 bucket name |
| `S3_PREFIX` | No | `detection-reports/` | S3 key prefix |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `CLOUDFRONT_DISTRIBUTION_ID` | No | — | CloudFront distribution for cache invalidation |

## Output

### Detection report
```
/output/
  report.json           # Parsed metrics + screenshot paths
  screenshots/
    playwright.webp     # Vanilla Playwright baseline
    puppeteer.webp      # Vanilla Puppeteer baseline
    owl-windows.webp    # Owl Browser with Windows profile
    owl-macos.webp      # Owl Browser with macOS profile
    owl-linux.webp      # Owl Browser with Linux profile
```

### Benchmark
```
/output/
  benchmark.json        # Timing data for all three browsers
```

Both files are overwritten on each run — no historical data stored.

## Benchmark Methodology

All three browsers are benchmarked sequentially in the same Docker container on the same machine:

1. **Cold start** — Playwright/Puppeteer: launch a new browser process + create page. Owl Browser: create a new context within the running engine.
2. **Navigation** — Navigate to `https://example.com` and wait for `networkidle`.
3. **Screenshot** — Capture a viewport screenshot.
4. **Full cycle** — Create → navigate → screenshot → close.

Each step is timed individually. 10 iterations per browser. Results include min, max, avg, median, p95, and raw timing arrays so anyone can verify.

The architectural difference: Playwright and Puppeteer launch a new OS process for each browser instance. Owl Browser creates lightweight contexts within an already-running engine — no process spawn overhead.

## VPS Deployment

### One-time setup

```bash
# Login to GitHub Container Registry
echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Create env file
sudo nano /etc/owl-report.env
# Paste your production config (OWL_BROWSER_URL, token, AWS creds)

# Test detection report
docker pull ghcr.io/olib-ai/owl-detection-report:latest
docker run --rm --network host --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest

# Test benchmark
docker run --rm --network host --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest --benchmark

# Set up cron
crontab -e
# 0 3 * * * docker run --rm --network host --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest >> /var/log/owl-report.log 2>&1
# 0 4 * * 0 docker run --rm --network host --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest --benchmark >> /var/log/owl-benchmark.log 2>&1
```

### Updating

```bash
docker pull ghcr.io/olib-ai/owl-detection-report:latest
# Next cron run will use the new image
```
