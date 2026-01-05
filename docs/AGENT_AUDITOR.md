# Agent: Auditor
**Role:** Verification and durability enforcement

## Objective
Verify sequestration and enforce durability requirements before XCR is minted.

## Key Logic (Code-Accurate)
1. **Verification:** Audits use a 1% error rate and project health to determine pass/fail.
2. **Minting:** On pass, XCR is minted for that year’s verified sequestration.
3. **Clawback:** On fail, 50% of lifetime XCR is burned and the project is marked failed.
4. **Reversals:** Failed projects return previously sequestered tonnes to the atmosphere.
5. **No Direct Policy Feedback:** Sentiment and R‑multipliers are not adjusted directly by the auditor.
