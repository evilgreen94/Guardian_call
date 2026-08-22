# Pre-Merge Review

Review a proposed Guardian Call change before it is committed to main.

## Steps

1. Read canonical project context and scope-freeze rule.
2. Inspect `git diff`.
3. Run the complete test suite.
4. Review for:
   - Gemini/Risk/Canary boundary violations;
   - fail-safe regressions;
   - secret leakage;
   - raw OTP/password logging;
   - fake observability;
   - scope creep;
   - unused dependencies;
   - duplicate lab architecture;
   - changes to existing M0 behavior.
5. Classify findings:
   - CRITICAL
   - HIGH
   - MEDIUM
   - LOW
   - NONE
6. End with one:
   - `SAFE TO COMMIT`
   - `FIX BEFORE COMMIT`
   - `REJECT CHANGE`
7. Do not modify files during review.
