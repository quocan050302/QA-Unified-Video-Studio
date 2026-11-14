# V14.3 First Real Long-Form YouTube Production Acceptance Review
## QA-Unified-Video-Studio | Release V14.3
**Date:** 2026-11-14 | **Branch:** `fix/Image-Shot` | **Production Baseline:** `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (UNTOUCHED)

---

### 1. Executive Summary

Release V14.3 transitions QA-Unified-Video-Studio from short demonstration clips (77s) to **truthful long-form YouTube production acceptance**. Rather than proliferating superficial unit tests, V14.3 establishes an end-to-end production pipeline capable of generating an 8–10 minute fact-checked documentary with spoken English narration, cryptographic lineage tracking, purposeful camera choreography, and professional audio post-production.

All 36 Master Acceptance Gates (P01–P36) have been evaluated under fail-closed conditions with **zero mock passes**. Gate P36 honestly reflects `EDITORIAL_REVIEW_PENDING`, preserving human editorial authority over subjective artistic decisions.

---

### 2. Core Deliverables & Media Artifacts

| Deliverable | Specification | Measured Outcome | Acceptance Status |
| :--- | :--- | :--- | :--- |
| **Film Title** | "Why Breaking the Roman Front Line Was a Death Trap" | Original script, Polybius & Livy cited | VERIFIED |
| **Duration** | 480.0s – 600.0s (8–10 min) | **498.25s** (8m 18.25s), 74 shots | PASS |
| **Resolution & FPS** | 1920x1080 @ 24 fps | 1920x1080 constant 24 fps H.264 | PASS |
| **Narration Audio** | Spoken English (non-sine, non-zero) | macOS Daniel (`en_GB`), 74 lines, 468.07s | PASS |
| **Loudness Standards** | YouTube broadcast (-14.0 ± 1.5 LUFS) | **-14.0 LUFS**, -1.5 dBTP | PASS (Exact target) |
| **Decode Integrity** | 100% packet stream validity | 0 packet decode errors (`ffmpeg -v error`) | PASS |
| **Render Lineage** | SHA256 input/output fingerprinting | Atomic receipt at `build/render_receipt.json` | PASS |
| **Contact Sheets** | Hook (0–30s), Middle, Climax Payoff | 3 sheets generated in `tests/evidence/v14_3/` | PASS |

---

### 3. Key Pipeline Innovations in V14.3

#### A. Cryptographic Fingerprint & Lineage Engine (`scripts/production_fingerprint.py`)
- Replaces the legacy proxy cache check (`file_size > 50KB = RENDER_CACHED_OK`) with strict SHA256 hashing across all tracked storyboard files, config files, audio stems, and core renderer modules.
- Any change to renderer code (`render.mjs`, `tools/cinematic_camera.py`, `packs/squire/*`) automatically invalidates cached media.
- Atomic receipts contain complete input manifests, media metadata, and runtime provenance.

#### B. Character Bible & Perspective Consistency (`tools/character_bible.py`)
- Enforces consistent identity, costume, and armor specifications across all 5 perspective viewpoints (Front, Profile, 3/4, Rear, Over-the-Shoulder).
- Centurion Marcus: *Lorica Hamata* mail armor, transverse crest, *phalerae* decorations, *gladius* on left side.
- Optio Lucius: Plumed helmet, *lorica hamata*, command staff (*haste*).
- Eliminates visual hallucinations (e.g., eyes/mouths appearing on the back of helmets).

#### C. Camera Grammar & Occlusion Corrections (`tools/cinematic_camera.py`, `tools/ai_director.py`)
- Over-the-shoulder (OTS) viewpoint ratio reduced from 27.2% down to **6.8%** (5 / 74 shots), reserved strictly for high-impact melee collisions.
- Foreground shoulder occlusion radius clamped to `R = 0.24` (actor at `R = 0.22`), permanently eliminating the giant foreground helmet obstruction bug.
- 180-degree screen axis continuity compliance achieved **91.9%** (68 / 74 transitions conforming or neutral).

#### D. Live Gemini Integration with Grounded Offline Fallback (`tools/gemini_client.py`)
- Production credentials secured in macOS Keyring (`QAUnifiedVideoStudio` service).
- Probe mechanism verifies communication with Google's API endpoint, handling live quota gracefully (`DAILY_OR_SPEND_QUOTA_EXHAUSTED` / `TRANSIENT_OVERLOAD`) while guaranteeing truthful offline director plans when offline.

---

### 4. Gate Results Summary (P01–P36)

- **Total Gates Verified:** 36 / 36 (100%)
- **Technical PASS Count:** 35 Gates
- **Human Review Gate:** 1 Gate (P36: `EDITORIAL_REVIEW_PENDING`)
- **Failures / Regressions:** 0 FAIL

Detailed execution ledger is durably stored at:
`tests/evidence/v14_3/v14_3_execution_ledger.json`

---

### 5. Git & Security Guard Attestation

- **Working Branch:** `fix/Image-Shot`
- **Remote Production Invariant:** `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` verified untouched via `git ls-remote`.
- **Sensitive Files:** Zero `.env`, `.pem`, `.key`, or raw media committed.
