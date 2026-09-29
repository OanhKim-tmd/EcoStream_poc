---
name: audit
description: Inspect Query Log (detected anomalies) and Assumption Log (applied conservative formulas & confidence penalties) from EcoStream pipeline runs.
user-invocable: true
disable-model-invocation: false
---

# EcoStream Audit Trail Inspector (Query Log & Assumption Log)

Inspect non-blocking anomalies detected by subagents, applied IPCC/TCVN conservative assumptions, and confidence score penalty deductions.

## Usage
- `/audit` : Inspect the most recent run
- `/audit <run_id>` : Inspect a specific run ID

## Procedure
Run the audit inspection script:
```bash
python -c "
import os, json
runs = sorted([d for d in os.listdir('runs') if os.path.isdir(os.path.join('runs', d))], reverse=True)
target = '$ARGUMENTS'.strip() or (runs[0] if runs else None)
if not target:
    print('No runs found in runs/ directory.')
    exit()
q_path = os.path.join('runs', target, 'intermediate', 'query_log.json')
a_path = os.path.join('runs', target, 'intermediate', 'assumption_log.json')
print(f'=== AUDIT TRAIL FOR RUN: {target} ===\n')
if os.path.exists(q_path):
    with open(q_path, 'r', encoding='utf-8') as f:
        queries = json.load(f)
        print(f'--- Query Log ({len(queries)} entries) ---')
        for q in queries:
            print(f'[{q[\"query_id\"]}] ({q[\"scope\"]}) {q[\"field_name\"]}: {q[\"detected_issue\"]} -> {q[\"action_taken\"]}')
if os.path.exists(a_path):
    with open(a_path, 'r', encoding='utf-8') as f:
        assumptions = json.load(f)
        print(f'\n--- Assumption Log ({len(assumptions)} entries) ---')
        for a in assumptions:
            print(f'[{a[\"assumption_id\"]}] {a[\"parameter_name\"]} = {a[\"assumed_value\"]} {a[\"assumed_unit\"]} | Penalty: -{a[\"confidence_penalty\"]*100:.1f}% | {a[\"justification\"]}')
"
```
