[English](README.md) | [中文](README_CN.md)

---

# ERLE Analyzer

**Echo Return Loss Enhancement Offline Analyzer**

A professional AEC (Acoustic Echo Cancellation) performance evaluation tool for offline testing and ERLE metric analysis.

---

## Features

### Core Functionality

| Feature                   | Description                                                                    |
| ------------------------- | ------------------------------------------------------------------------------ |
| **Dual Format Support**   | Supports WAV and PCM formats with auto-detection                               |
| **Segmented Calculation** | Default 100ms segments, configurable                                           |
| **Energy Threshold**      | -46 dBFS threshold (compliant with ITU-T G.168 and WebRTC standards)           |
| **Silence Detection**     | Dual detection for reference and microphone signals, excludes invalid segments |
| **Double-Talk Detection** | Auto-excludes double-talk segments when ERLE < -3 dB                           |
| **Statistical Analysis**  | Mean, std dev, min, max, median, P95, P99                                      |
| **Rating System**         | Excellent/Good/Fair/Poor four-level evaluation                                 |
| **Histogram**             | Visual ERLE distribution                                                       |
| **Batch Analysis**        | Directory traversal and summary reports                                        |

### Output Formats

- **Text Report**: Complete analysis report (with histogram)
- **JSON Report**: Structured data for further processing
- **CSV Report**: Batch analysis results table
- **Markdown Report**: Beautiful summary report

---

## Installation

### Requirements

- Python 3.7+
- No additional dependencies (uses Python standard library only)

### Installation Steps

```bash
# 1. Clone or download the project
cd /path/to/erle-analyzer

# 2. Make scripts executable (optional)
chmod +x erle_analyzer.py
chmod +x erle_batch_analyze.py
```

---

## Quick Start

### Single File Analysis

#### Basic Usage (Rec and Out only)

```bash
# Simplest: just rec and out files
python erle_analyzer.py -r rec.wav -o out.wav

# Save report
python erle_analyzer.py -r rec.wav -o out.wav \
    --report result.txt
```

#### With Reference Signal (More accurate silence detection)

```bash
# With ref file, can more accurately exclude far-end silence segments
python erle_analyzer.py -r rec.wav -f ref.wav -o out.wav \
    --report result.txt --json result.json
```

#### WAV Format (Recommended)

```bash
# WAV format auto-detects sample rate
python erle_analyzer.py -r rec.wav -o out.wav
```

#### PCM Format

```bash
# Specify sample rate (8kHz)
python erle_analyzer.py -r rec.pcm -o out.pcm \
    --sample-rate 8000

# Specify sample rate (16kHz)
python erle_analyzer.py -r rec.pcm -o out.pcm \
    --sample-rate 16000
```

### Batch Analysis

```bash
# Analyze all test files in directory
python erle_batch_analyze.py /path/to/test_audio

# Save reports in multiple formats
python erle_batch_analyze.py /path/to/test_audio \
    --csv results.csv \
    --md results.md
```

---

## Command Line Arguments

### erle_analyzer.py (Single File Analysis)

| Argument         | Short | Description                                             | Default |
| ---------------- | ----- | ------------------------------------------------------- | ------- |
| `-r, --rec`      | -     | Microphone input file (required)                        | -       |
| `-f, --ref`      | -     | Reference signal file (optional, for silence detection) | none    |
| `-o, --out`      | -     | AEC output file (optional, defaults to rec)             | none    |
| `--sample-rate`  | -     | Sample rate (required for PCM files)                    | 16000   |
| `--segment-size` | -     | Segment size (ms)                                       | 100     |
| `--report, -R`   | -     | Output text report path                                 | none    |
| `--json, -J`     | -     | Output JSON report path                                 | none    |
| `--quiet, -q`    | -     | Quiet mode (only output ERLE value)                     | no      |

### erle_batch_analyze.py (Batch Analysis)

| Argument           | Short | Description                      | Default |
| ------------------ | ----- | -------------------------------- | ------- |
| `directory`        | -     | Test files directory (required)  | -       |
| `--sample-rate`    | -     | Sample rate                      | 16000   |
| `--segment-size`   | -     | Segment size (ms)                | 100     |
| `--csv`            | -     | Output CSV report path           | none    |
| `--md, --markdown` | -     | Output Markdown report path      | none    |
| `--quiet, -q`      | -     | Quiet mode (output summary only) | no      |

---

## Output Report

### Text Report Example

```
================================================================================
                    ERLE Offline Analysis Report
================================================================================
Analysis Time: rec.wav
Generated: 2026-03-12 15:30:45

--------------------------------------------------------------------------------
📁 File Information
--------------------------------------------------------------------------------
Microphone File (Rec): rec.wav
Reference File (Ref)  : ref.wav
Output File (Out)     : out.wav
Sample Rate: 16000 Hz
Duration: 30.00 seconds

--------------------------------------------------------------------------------
📊 Segment Statistics
--------------------------------------------------------------------------------
Total Segments: 300 segments (100ms/segment)
Valid Segments: 270 segments (90.0%)
Excluded Segments: 30 segments (10.0%)
  - Reference Silence: 10 segments
  - Microphone Silence: 5 segments
  - Double-Talk: 15 segments

--------------------------------------------------------------------------------
📈 ERLE Statistics
--------------------------------------------------------------------------------
Mean    : 22.35 dB
Std Dev : 4.21 dB
Min     : 12.50 dB
Max     : 31.80 dB
Median  : 23.10 dB
P95     : 28.50 dB
P99     : 30.20 dB

--------------------------------------------------------------------------------
🏆 Evaluation Result
--------------------------------------------------------------------------------
Rating: Good
Description: AEC working normally with small amount of residual echo

--------------------------------------------------------------------------------
📊 ERLE Distribution Histogram
--------------------------------------------------------------------------------
     10.0-13.0 dB | ████                                     12 (  4.4%)
     13.0-16.0 dB | ██████                                   18 (  6.7%)
     16.0-19.0 dB | ██████████                               30 ( 11.1%)
     19.0-22.0 dB | ████████████████                         48 ( 17.8%)
     22.0-25.0 dB | ██████████████████████                   60 ( 22.2%)
     25.0-28.0 dB | ████████████████████                     54 ( 20.0%)
     28.0-31.0 dB | ██████████                               30 ( 11.1%)
     31.0-34.0 dB | ████                                     12 (  4.4%)
     34.0-37.0 dB | ██                                        6 (  2.2%)
     37.0-40.0 dB |                                          0 (  0.0%)

================================================================================
                         End of Report
================================================================================
```

### Rating Standards

| Rating        | ERLE Range | Description                                         |
| ------------- | ---------- | --------------------------------------------------- |
| **Excellent** | ≥ 25 dB    | AEC performance good, echo cancelled thoroughly     |
| **Good**      | 15-25 dB   | AEC working normally with small residual echo       |
| **Fair**      | 10-15 dB   | AEC effect average, audible echo may exist          |
| **Poor**      | < 10 dB    | AEC effect poor, check configuration or environment |

---

## Batch Analysis

### File Naming Convention

The batch analysis tool automatically matches file pairs with the following naming patterns:

| Type           | Pattern                                 | Description                     |
| -------------- | --------------------------------------- | ------------------------------- |
| **Microphone** | `{base}_mic.wav` or `{base}_rec.wav`    | Microphone input signal         |
| **Reference**  | `{base}_lpb.wav` or `{base}_ref.wav`    | Far-end reference signal        |
| **Output**     | `{base}_output.wav` or `{base}_out.wav` | AEC processed output (optional) |

### Example Directory Structure

```
test_audio/
├── 001_farend-singletalk_mic.wav
├── 001_farend-singletalk_lpb.wav
├── 001_farend-singletalk_output.wav
├── 002_farend-singletalk_mic.wav
├── 002_farend-singletalk_lpb.wav
└── 002_farend-singletalk_output.wav
```

### Batch Analysis Output

```bash
$ python erle_batch_analyze.py /path/to/test_audio --md results.md

================================================================================
                    ERLE Batch Analysis Tool v1.0
================================================================================
Analysis Directory: /path/to/test_audio
Sample Rate: 16000 Hz
Segment Size: 100 ms

Found 2 test file pairs

[1/2] Analyzing: 001
  ERLE: 22.35 dB, Rating: Good
[2/2] Analyzing: 002
  ERLE: 18.72 dB, Rating: Good

================================================================================
                           Summary
================================================================================
Test Files: 2
Average ERLE: 20.54 dB
Max ERLE: 22.35 dB
Min ERLE: 18.72 dB

Rating Distribution:
  Good: 2 files

Markdown report saved: results.md
```

---

## Technical Principles

### ERLE Calculation Formula

```
ERLE = 10 × log10(P_rec / P_out)  [dB]

Where:
- P_rec = Microphone input signal power (with echo)
- P_out = AEC processed output signal power (residual echo)
```

### Energy Thresholds (Compliant with ITU-T G.168 and WebRTC)

| Parameter                 | Threshold | Description                                                                    |
| ------------------------- | --------- | ------------------------------------------------------------------------------ |
| **Reference Signal**      | -46 dBFS  | Below this value, segment is excluded as silence (only when ref file provided) |
| **Microphone Signal**     | -46 dBFS  | Below this value, segment is excluded as silence                               |
| **Double-Talk Detection** | -3 dB     | Below this ERLE value, segment is excluded as double-talk                      |

### Segmentation Process

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Read audio file (WAV or PCM)                        │
│  - Rec (required): Microphone input signal                 │
│  - Out (optional): AEC output signal (uses Rec if not provided) │
│  - Ref (optional): Reference signal (for far-end silence detection) │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Segment by 100ms (default)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Energy check for each segment (if Ref file provided)│
│  - Reference signal < -46 dBFS ? → exclude (silence)       │
│  - Microphone signal < -46 dBFS ? → exclude (silence)      │
│                                                              │
│  If no Ref file, only check microphone signal               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Calculate ERLE for valid segments                   │
│  - ERLE = 10 × log10(P_rec / P_out)                         │
│  - ERLE < -3 dB ? → exclude (double-talk)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Statistical analysis                                 │
│  - Mean, std dev, min, max                                   │
│  - Median, P95, P99 percentiles                             │
│  - Histogram distribution                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Generate report                                      │
│  - Text report (with histogram)                             │
│  - JSON report (structured data)                            │
│  - CSV report (batch analysis)                              │
└─────────────────────────────────────────────────────────────┘
```

### Why Exclude Silence and Double-Talk Segments?

**Silence Segment Problem**:

```
When both ends are silent:
- Ref ≈ 0 (far-end silence)
- Rec ≈ local noise
- Out ≈ Rec (AEC has no echo to cancel)

ERLE = 10 × log10(P_rec / P_out) ≈ 10 × log10(1) = 0 dB

→ Silence segments severely pull down overall ERLE evaluation
```

**Double-Talk Segment Problem**:

```
When both ends speak simultaneously:
- Rec = near-end speech + echo
- Out = near-end speech + residual echo

Since near-end speech is added, Out may become > Rec
ERLE = 10 × log10(P_rec / P_out) < 0 dB

→ Double-talk segments produce negative ERLE, interfering with evaluation
```