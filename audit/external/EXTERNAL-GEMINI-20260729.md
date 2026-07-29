# Gemini — adversarial audit report (2026-07-29)

> Converted verbatim from the operator's uploaded `.docx` (the CUI guard blocks that
> extension in-repo). Text only; original formatting and any tables are flattened.

# Schedule Forensics: Adversarial Audit & Verification Report
Target Repository: schedule-forensicsAuthor: Automated Audit EngineDate: July 2026
## 1. Executive Summary
This report outlines two critical failures identified during the recent adversarial test sweep (test_h2_offset.py and test_h3_input.py) and proposes fixes for evaluation.
## 2. Detailed Findings & Proposed Fixes
### Finding 1: Calendar Model Validation Error (H2)
• Test File: test_h2_offset.py• Symptom: ValidationError for Calendar (start, end extra inputs forbidden)• Fix: Update Calendar model in schedule_forensics/engine/cpm.py to accept start and end fields.
### Finding 2: Reconcile Magnitudes Signature Mismatch (H3)
• Test File: test_h3_input.py• Symptom: TypeError: _reconcile_magnitudes() missing required positional arguments• Fix: Add default values for days_locked and pct_locked.
## 3. Prompt for Claude Code
Copy and paste the text below into Claude Code to begin the adversarial verification process:You are an expert software engineer and adversarial code reviewer. Your task is to analyze the following two findings from our test suite sweep on the schedule-forensics repository, verify if the findings are correct, and attempt to disprove or validate them with code patches.1. Finding H2: est_h2_shift_boundary_violation fails with a Pydantic ValidationError because Calendar(start='08:00', end='17:00') encounters extra field rejections.   - Objective: Inspect schedule_forensics/engine/cpm.py, determine if Calendar should support start/end fields or if the test is misconfigured, and implement the correct fix.2. Finding H3: est_h3_malformed_magnitude fails with a TypeError due to missing required arguments days_locked and pct_locked in _reconcile_magnitudes().   - Objective: Inspect schedule_forensics/web/app.py, evaluate the function signature, and add appropriate default values or update the test.Please review the codebase, challenge these findings if our test assumptions are flawed, or apply the robust fixes and run pytest to verify all tests pass.
