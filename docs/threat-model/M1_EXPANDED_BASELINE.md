# M1 Expanded Adversarial Baseline

## Evaluation boundary

This baseline was captured on 2026-08-24 in offline oracle mode. All 57
predefined M0 `ScamSignals` objects were processed independently through the
real `GuardianPipeline.process_signals()`, RiskEngine, and CanaryPolicy. Gemini
was not initialized, no API key was required, and no network access occurred.

Expected outcomes are diagnostic ground truth for evaluating M0. They are not
an implicit specification for ScamSignals v2, RiskEngine v2, or future Canary
policy. No production behavior was changed to satisfy these expectations.

## Global result

```text
M1 ADVERSARIAL BASELINE // M0 ENGINE

CASES                   57
PASS                    24
RISK MISMATCH           10
CANARY MISMATCH          0
MODEL GAP               22
AMBIGUOUS                1
```

The original `baseline_20` cohort retained its exact prior result map. The
expansion added 37 contrastive cases without rewriting historical findings.

## Family results

Family memberships overlap; these rows do not sum to the global total.

| Family | Cases | Pass | Model gap | Risk | Canary | Ambiguous |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OTP / authentication | 14 | 12 | 2 | 0 | 0 | 0 |
| Payment card / CVV | 11 | 1 | 7 | 2 | 0 | 1 |
| Money movement | 11 | 5 | 3 | 3 | 0 | 0 |
| Remote device control | 9 | 8 | 1 | 0 | 0 | 0 |
| Account takeover / recovery | 13 | 3 | 9 | 1 | 0 | 0 |
| Crypto / wallet assets | 5 | 1 | 3 | 1 | 0 | 0 |
| Apparent credibility | 15 | 4 | 5 | 6 | 0 | 0 |
| Manipulation / social engineering | 12 | 7 | 4 | 1 | 0 | 0 |
| Cross-domain masking | 21 | 9 | 12 | 0 | 0 | 0 |

## Constitutional coverage

| Principle | Cases | Pass | Model gap | Risk | Canary | Ambiguous |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C1: Knowledge is not authentication | 15 | 4 | 5 | 6 | 0 | 0 |
| C2: Trust does not cancel dangerous behavior | 26 | 12 | 14 | 0 | 0 | 0 |
| C3: Sensitive requests outweigh apparent legitimacy | 37 | 14 | 22 | 1 | 0 | 0 |

## Language coverage

| Language | Cases | Share |
| --- | ---: | ---: |
| Spanish | 35 | 61.4% |
| English | 22 | 38.6% |

The contrastive expansion itself contains 35 Spanish and 2 English cases. All
conversation data is synthetic.

## Model gaps

1. `isp_card_cvv`: payment-card and card-security-code requests.
2. `social_network_otp_takeover`: login approval.
3. `ecommerce_fake_cancellation`: card-security-code request.
4. `bizum_payment_app`: payment-app authorization.
5. `crypto_seed_phrase`: seed-phrase request.
6. `gift_card_payment`: gift-card payment.
7. `recovery_code_takeover`: recovery code, disabling 2FA, and recovery-identity change.
8. `long_confidence_scam`: card-security-code request.
9. `card_number_request_es`: payment-card request.
10. `card_expiry_request_es`: card-expiry request.
11. `cvv_indirect_private_context_es`: card-security-code request.
12. `cvv_mixed_safety_malicious_es`: card-security-code request.
13. `cash_withdrawal_request_es`: cash-withdrawal request.
14. `remote_screen_share_es`: screen-sharing request.
15. `login_approval_private_context_es`: login approval.
16. `recovery_email_change_es`: recovery-email change.
17. `recovery_phone_change_es`: recovery-phone change.
18. `disable_2fa_request_es`: disabling 2FA.
19. `password_reset_link_request_es`: directed password-reset link.
20. `cloud_recovery_code_request_en`: recovery-code request.
21. `crypto_private_key_request_es`: private-key request.
22. `crypto_wallet_recovery_phrase_en`: seed-phrase request.

These concepts were not mapped into unrelated M0 fields. Risk and Canary still
ran on each case's honest M0 projection, but downstream differences were not
misclassified as engine failures.

## RiskEngine mismatches

1. `safe_account_transfer`: expected `CRITICAL`; M0 returned `HIGH`.
2. `legitimate_bank_notification`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
3. `legitimate_isp_sale`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
4. `private_data_no_dangerous_request`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
5. `card_warning_private_name_es`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
6. `card_self_entry_private_context_es`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
7. `transfer_ordinary_discussion_es`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
8. `transfer_legitimate_do_not_move_es`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
9. `self_service_recovery_full_context_es`: expected `NORMAL`; M0 returned `SUSPICIOUS`.
10. `crypto_seed_warning_es`: expected `NORMAL`; M0 returned `SUSPICIOUS`.

Nine mismatches are false-positive calibration findings: M0 elevates benign
identity claims or broad financial context despite the absence of a dangerous
request. The safe-account case is the sole under-classification in this set;
M0 still returns `HIGH`, so Canary authorizes a warning.

## Canary mismatches

None. Canary consistently applied the current M0 authorization table to the
risk level it received.

## Ambiguous case

- `ambiguous_security_digits`: no defensible single expected interpretation was
  forced, even though card-security-code language is itself outside M0.

## Interpretation

M0 is strongest where its schema directly represents the dangerous capability:
OTP disclosure, password disclosure, money transfer, and remote device access.
Its largest blind spots are card assets, account-control actions, wallet secrets,
payment-app authorization, gift cards, cash withdrawal, and screen sharing.

The contrastive controls also show that unverified organizational claims and
broad financial or crypto context can create `SUSPICIOUS` results without a
dangerous requested action. These findings are evidence for later design work;
they are not fixes and do not authorize a production policy change.
