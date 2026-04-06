# Owl Detection Report Generator

Automated daily comparison of [Owl Browser](https://owlbrowser.net) vs vanilla Playwright and Puppeteer on [CreepJS](https://abrahamjuliot.github.io/creepjs/) — the industry-standard fingerprint detection tool.

Generates a structured JSON report with screenshots showing that Owl Browser produces unique fingerprints per OS profile while Playwright and Puppeteer leak identical real device fingerprints.

Results are displayed at [owlbrowser.net/detection-test](https://owlbrowser.net/detection-test).

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

### 3. Run

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/output:/output \
  ghcr.io/olib-ai/owl-detection-report:latest
```

### 4. Set up daily cron

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 3am UTC)
0 3 * * * docker run --rm --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest >> /var/log/owl-report.log 2>&1
```

> **Note:** When using S3 upload, the `-v` volume mount is optional since the report goes directly to S3. Include it if you also want a local copy.

## Build from source

```bash
git clone https://github.com/Olib-AI/owl-detection-report.git
cd owl-detection-report
docker build -t owl-detection-report .
docker run --rm --env-file .env -v $(pwd)/output:/output owl-detection-report
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

The report is overwritten on each run — no historical data stored.

## How It Works

1. Launches vanilla **Playwright** Chromium against CreepJS (baseline)
2. Launches vanilla **Puppeteer** Chromium against CreepJS (baseline)
3. Launches **Owl Browser** with Windows, macOS, and Linux OS profiles against CreepJS
4. For each browser: captures a full-page screenshot and extracts detection metrics
5. Builds `report.json` with parsed fingerprint hashes, headless detection scores, GPU info, etc.
6. Optionally uploads everything to S3

### What the report shows

- **Playwright & Puppeteer** have identical fingerprint hashes (canvas, WebGL, audio, fonts) — they leak the real device
- **Owl Browser** has completely different hashes per OS profile — genuine C++ source-level spoofing
- Headless detection: Playwright `100%`, Puppeteer `100%`, Owl Browser `0%`
- GPU: Playwright/Puppeteer expose SwiftShader (dead giveaway), Owl shows real GPU profiles

## VPS Deployment

### On the VPS (one-time setup)

```bash
# Login to GitHub Container Registry
echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Create env file
sudo nano /etc/owl-report.env
# Paste your production config (OWL_BROWSER_URL, token, AWS creds)

# Test run
docker pull ghcr.io/olib-ai/owl-detection-report:latest
docker run --rm --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest

# Set up cron
crontab -e
# 0 3 * * * docker run --rm --env-file /etc/owl-report.env ghcr.io/olib-ai/owl-detection-report:latest >> /var/log/owl-report.log 2>&1
```

### Updating

```bash
docker pull ghcr.io/olib-ai/owl-detection-report:latest
# Next cron run will use the new image
```
