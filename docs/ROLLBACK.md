# AERIS-TWIN — Rollback & Version Recovery Runbook

This guide provides step-by-step instructions for inspecting, checking out, and rolling back to any verified checkpoint in **AERIS-TWIN**.

---

## 1. Quick Checkpoint Reference

| Checkpoint Name | Purpose | Git Reference |
| :--- | :--- | :--- |
| `checkpoint: baseline` | Initial project baseline | `0328226` or tag `v0.1.0-baseline` |
| `checkpoint: audit-fixes` | Physics & terminology fixes | `c3635fa` or tag `v0.2.0-audit` |
| `checkpoint: telemetry-stable` | Real-time honest telemetry fix | `aa03683` or tag `v0.3.0-telemetry-stable` |
| `checkpoint: final-validated` | Complete verified system | `HEAD` or tag `v1.0.0-final-validated` |

---

## 2. Viewing Available Checkpoints

To list all checkpoints, tags, and commit history:

```bash
# List all release tags and checkpoints
git tag -l -n9

# View formatted checkpoint commit log
git log --oneline --decorate -n 10
```

---

## 3. How to Restore / Rollback

### Scenario A: Rollback to Before the Real-Time Telemetry Changes
```bash
# Rollback working tree to audit-fixes checkpoint
git checkout c3635fa

# Or reset main branch to audit-fixes (Warning: discards uncommitted changes)
git reset --hard c3635fa
```

### Scenario B: Rollback to Telemetry Stable Baseline
```bash
git checkout aa03683
# or
git checkout v0.3.0-telemetry-stable
```

### Scenario C: Return to the Latest Final Validated Version
```bash
git checkout main
git pull origin main
```

---

## 4. Recovering from an Experimental Branch

When starting a high-risk change, create an experimental branch first:

```bash
# 1. Create and switch to experiment branch
git checkout -b experiment/new-feature

# 2. If experiment fails, safely return to main
git checkout main
git branch -D experiment/new-feature
```

---

## 5. Verification Commands After Any Rollback

Always run the full test suite after restoring a checkpoint to verify system health:

```bash
# Run all Python backend tests
python -m pytest -v

# Run frontend build check
npm run build
```
