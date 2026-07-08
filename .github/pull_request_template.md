## Description
Please include a brief summary of the changes, the rationale behind them, and any relevant context or issue references.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Refactoring (no functional changes, code style improvements)
- [ ] Documentation update
- [ ] Test suite updates

## 🔒 Safety & Security Checklist
Please verify that your changes adhere to the codebase security rules:
- [ ] **Domain Whitelist**: If modifying write operations, ensure all recipient domains are verified against `GWS_ALLOWED_DOMAINS`.
- [ ] **PII Scrubber**: If adding new read fields, verify that no sensitive data (emails, phone numbers, meeting details) bypasses `@scrub_pii` masking.
- [ ] **Rate Limiting**: Verify that all Google Calendar API requests adhere to the 100ms global throttle (`@rate_limited`).
- [ ] **Audit Logging**: Confirm that all new modifying actions log timestamped JSON entries to `audit.log` via `audit_log()`.
- [ ] **No Hardcoded Secrets/Personal Info**: Verify no developer credentials, personal emails, or private names are hardcoded.

## 🧪 Testing & Verification
Describe the tests you ran to verify your changes.
- [ ] **Unit Tests**: All existing mock-based unit tests pass.
  ```bash
  .venv/bin/pytest
  ```
- [ ] **Formatting & Linting**: Checked and formatted via Ruff.
  ```bash
  .venv/bin/ruff format && .venv/bin/ruff check --fix
  ```

## 📄 License & Compliance
- [ ] Code is licensed under the MIT License and includes copyright & warning headers.
- [ ] Pre-commit status checks are green.
