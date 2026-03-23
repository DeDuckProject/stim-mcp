# QA Report — 2026-03-23

## Feature Tested
Circuit privacy improvements: 128-bit UUID circuit IDs (B) and privacy notice in `hello_quantum` + README (A).

## Target Server
Local — Stim version: 1.15.0

## Changes Analyzed
Branch: master (uncommitted)
Files changed: `circuit_store.py`, `server.py`, `README.md`

## Test Results

| # | Description | Tool Called | Inputs | Response | Result | Notes |
|---|-------------|-------------|--------|----------|--------|-------|
| 1 | hello_quantum returns privacy_notice | `hello_quantum` | `{}` | `{"status":"ok","stim_version":"1.15.0","active_sessions":0,"privacy_notice":"..."}` | PASS | All 4 keys present |
| 2 | circuit_id is 32 hex chars (128-bit) | `create_circuit` | Bell state circuit | `{"circuit_id":"c398bf98775b46e583e9b242b9cd131b"}` | PASS | len=32, valid hex |
| 3 | sample_circuit works with 32-char ID | `sample_circuit` | `circuit_id=c398...`, `shots=500` | `{"flip_rates":[0.5,0.5]}` | PASS | Bell state ~50% correct |
| 4 | get_circuit_diagram works with 32-char ID | `get_circuit_diagram` | `circuit_id=c398...`, `diagram_type=text` | ASCII diagram returned | PASS | |
| 5 | append_operation works with 32-char ID | `append_operation` | `circuit_id=c398...`, `DETECTOR rec[-1]` | `{"success":true}` | PASS | |
| 6 | inject_noise returns 32-char noisy circuit ID | `inject_noise` | `circuit_id=c398...`, `DEPOLARIZE1`, `p=0.01` | `{"noisy_circuit_id":"6bca8139d5a74082906d5c0c4df22ce8"}` | PASS | New ID also 32 chars |
| 7 | analyze_errors handles noisy circuit gracefully | `analyze_errors` | `circuit_id=6bca...` | `{"success":false,"error":"non-deterministic detectors..."}` | PASS | Expected Stim error for this circuit shape |
| 8 | Invalid 32-char circuit ID returns graceful error | `sample_circuit` | `circuit_id=deadbeef...deadbeef` | `{"success":false,"error":"No circuit found with id '...'"}` | PASS | |

## Summary
Total: 8 | Passed: 8 | Failed: 0 | Warnings: 0

## Issues Found
None.

## Passed Checks
- ✅ `hello_quantum` returns `privacy_notice` field
- ✅ Circuit IDs are 32 hex characters (128-bit, was 8)
- ✅ All tools (`sample_circuit`, `get_circuit_diagram`, `append_operation`, `inject_noise`, `analyze_errors`) accept and return 32-char IDs correctly
- ✅ `inject_noise` derivative circuits also get 32-char IDs
- ✅ Unknown circuit IDs return graceful `success: false` errors (no crash)
