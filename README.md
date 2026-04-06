# Owl Detection Report Generator

Automated detection report generator that compares [Owl Browser](https://owlbrowser.net) against vanilla Playwright (Chromium) on [CreepJS](https://abrahamjuliot.github.io/creepjs/).

Runs daily via cron. Produces structured JSON reports with captured HTML (rendered on the website inside Shadow DOM for interactive scrolling).

## Quick Start

```bash
docker build -t owl-detection-report .
docker run --rm \
  -e OWL_BROWSER_URL=http://your-owl-instance \
  -e OWL_BROWSER_TOKEN=your-token \
  -v $(pwd)/output:/output \
  owl-detection-report
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OWL_BROWSER_URL` | Yes | - | Owl Browser REST API endpoint |
| `OWL_BROWSER_TOKEN` | Yes | - | Owl Browser API token |
| `OUTPUT_DIR` | No | `/output` | Local output directory |
| `AWS_ACCESS_KEY_ID` | No | - | AWS credentials for S3 upload |
| `AWS_SECRET_ACCESS_KEY` | No | - | AWS credentials for S3 upload |
| `S3_BUCKET` | No | - | S3 bucket name |
| `S3_PREFIX` | No | `detection-reports/` | S3 key prefix |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `CLOUDFRONT_DISTRIBUTION_ID` | No | - | CloudFront distribution for cache invalidation |

## Output

```
/output/
  index.json
  2026-04-05/
    report.json       # structured data + full HTML per browser/OS
```

Each `report.json` contains per-OS profiles (Windows, macOS, Linux) with:
- Full captured HTML from CreepJS (rendered in Shadow DOM on the website)
- Parsed trust score, lies detected, bot detection status
- Per-category fingerprint results (canvas, WebGL, audio, fonts, etc.)

## Cron Setup

```bash
0 3 * * * docker run --rm --env-file /etc/owl-report.env -v /data/reports:/output ghcr.io/olib-ai/owl-detection-report
```

## How It Works

1. Launches vanilla Playwright Chromium against CreepJS (the baseline)
2. Launches Owl Browser with Windows, macOS, and Linux profiles against CreepJS
3. Captures full page HTML and extracts detection results
4. Generates a structured JSON report comparing the two
5. Optionally uploads everything to S3

The website renders the captured HTML inside Shadow DOM containers styled as browser windows, allowing users to scroll through and inspect the actual CreepJS results.
