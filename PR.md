## Description
This Pull Request implements the complete, production-ready features, middleware, security bounds, and test suite for the `gws-workspace-agent` Model Context Protocol (MCP) server. 

Key additions:
1. **Interactive Installer**: Built [setup.sh](setup.sh) and [setup.py](setup.py) to automate developer and user local configurations (venv setup, Google API credentials caching, and automated Claude Desktop JSON configuration updates).
2. **Hardened Tools**: Fully coded the read tools (`list_calendars`, `view_schedule`, `find_slots`) and modifying write tools (`create_event`, `move_event`, `modify_event`, `delete_event`).
3. **Safety & Policy Enforcers**: Integrated invitee whitelisting against `GWS_ALLOWED_DOMAINS` and double-booking checking using the free/busy calendar endpoint.
4. **Interactive Deletions**: Implemented the two-turn dry-run confirm flow for `delete_event` to prevent accidental event loss.
5. **PII Masking & Privacy**: Built post-processing filters supporting `none`, `redact` (phone/email scrub), and `metadata_only` redactions.
6. **Logging & Throttling**: Added a 100ms request limiter and append-only structured JSON audit log wrapper with restricted file permissions (`chmod 600`).
7. **Robust Tests**: Included a 19-case unit test suite with mock endpoints for all tools and CLI overrides.

## Type of Change
- [x] Bug fix (non-breaking change which fixes an issue)
- [x] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [x] Refactoring (no functional changes, code style improvements)
- [x] Documentation update
- [x] Test suite updates

## 🔒 Safety & Security Checklist
- [x] **Domain Whitelist**: Invitee domains verified against `GWS_ALLOWED_DOMAINS`.
- [x] **PII Scrubber**: Sensitive description and email data masked dynamically.
- [x] **Rate Limiting**: Rate limited to 100ms between calls.
- [x] **Audit Logging**: Structured log statements securely saved to `audit.log` (`chmod 600`).
- [x] **No Hardcoded Secrets/Personal Info**: Checked and confirmed that all developer emails/usernames are cleaned and generic.

## 🧪 Testing & Verification
All unit tests have been successfully verified locally:
- [x] **Unit Tests**: All 19 pytest cases passed.
- [x] **Formatting & Linting**: Checked and formatted via Ruff.

## 📄 License & Compliance
- [x] Code is licensed under the MIT License and includes copyright & warning disclaimers at the top of each file.
- [x] Pre-commit status checks are green.
