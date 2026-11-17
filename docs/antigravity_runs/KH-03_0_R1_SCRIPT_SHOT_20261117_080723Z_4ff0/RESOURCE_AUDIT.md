# KH-03.0.R1 — Resource & Performance Audit (`RESOURCE_AUDIT.md`)

- **Host Spec**: Windows 11, `12` logical CPUs, `31.75 GiB` physical RAM, GPU rasterizer `ANGLE D3D11 (Intel UHD Graphics 730)` via system Edge headless (`render.mjs`).
- **Thresholds Enforced**: Min free disk `>= 5.0 GiB`, min available RAM `>= 1.0 GiB`, worker concurrency capped `<= 2`.

## Observed Benchmarks (`G13_PERFORMANCE_DISK_SAFETY` + Full Render)

| Run Type | Observed Samples | Median Wall Time | Status |
|---|---|---|---|
| Full `1080x1920 @ 24fps` (`720` frames, `workers=2`) | Single full export + `tools/mix.py` | Render `~28–31s`, Mix `~5s` | `PASS` |
| `G13` Serial (`--from 0 --to 6 --scale 0.5 --workers 1`, 3 repeats) | `4.078s`, `4.047s`, `4.156s` | `4.078s` | `PASS` |
| `G13` Parallel (`--from 0 --to 6 --scale 0.5 --workers 2`, 3 repeats) | `3.859s`, `3.828s`, `3.891s` | `3.859s` (`1.057x`) | `PASS` |
| Monitored Resource Floor Across Full Suite | Disk min `52.55 GiB` free / RAM min `9.99 GiB` avail | `monitor_breached = false` | `PASS` |
