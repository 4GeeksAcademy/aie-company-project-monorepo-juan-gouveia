# Brasaland API tests

> **Status (2026-11-10): test plan.** This document lists the cases to cover before any test is written (ticket AUTH-088). The sections on running the tests, coverage and results will be completed once the suite is finished.

> _Spanish version: [TESTING.es.md](./TESTING.es.md)._

## Suites

| Suite | Folder | What it checks |
|---|---|---|
| **Authentication unit tests** (AUTH-088) | `tests/auth/` | The logic of each authentication endpoint: what it decides, not how it responds. They call each route's functions and their services directly, without an HTTP client. Shared fixtures in `tests/auth/conftest.py`: active, inactive and admin users, and a controlled clock. *Tests to be written in phases 3 and 4.* |
| **HTTP integration** | `tests/integration/` | The HTTP contract with the backoffice: protected routes, status codes, the `{"error": {...}}` format and headers. These are the router tests that already existed. They carry the `integration` marker, applied to the whole folder by `tests/integration/conftest.py`: 99 tests (214 cases with parametrization). |
| **Other** | `tests/core/` and `tests/domains/` | Configuration, security, email, errors, repositories, and the `incidents` and `suppliers` domains. |

## How to run them

*Preliminary; to be confirmed at the end.* From `services/brasaland-api/`:

```bash
uv sync --extra dev                      # installs pytest, pytest-cov and httpx
uv run pytest                            # the whole suite
uv run pytest tests/auth                 # authentication unit tests only
uv run pytest -m integration             # HTTP integration tests only
uv run pytest -m "not integration"       # everything except the HTTP tests
uv run pytest --cov                      # the whole suite with coverage
```

## Plan criteria

- **Logic, not HTTP.** Each test asserts a decision made by the application: which token is issued, which `ApiError` is raised and with which code, what is stored in the database. Tests don't check the JSON, the status codes set by FastAPI, or the framework's body validation. The rules in our own models (password length, forbidden fields) are tested, because they are business rules.
- **No HTTP and no network.** Tests use a temporary TinyDB database and the fake email sender (`tests/conftest.py`). Time is controlled through the logic's `now` and `expires_delta` parameters, never by waiting.
- **Priorities**, in this order:
  1. **token expiry**, because it's the regression that triggered the ticket;
  2. **security decisions**: don't reveal which emails exist, don't allow privilege escalation, and end sessions when the password changes;
  3. **the boundaries of the input rules**.
- **Three levels per endpoint:** happy path (**F**), edge case (**L**) and failure mode (**X**). Cases marked **(AI)** came out of the AI-assisted review (see below).
- **One module per endpoint**, plus `test_token.py` for token creation and validation, which every protected endpoint relies on.

## Cases by module

### `test_token.py` — access tokens and session validation

Covers `core/security.py` (create and decode) and `get_current_user`, the dependency used by every protected route.

| ID | Case | Expected decision | Why |
|---|---|---|---|
| TOK-F1 | Create a token | It carries `sub` = user ID; `exp − iat` = `ACCESS_TOKEN_EXPIRE_MINUTES` × 60 | Catches a change of units (seconds instead of minutes), exactly the kind of refactor behind the incident |
| TOK-F2 | Valid token in `get_current_user` | Returns the user from the database | The path every protected route takes |
| TOK-L1 | Token issued (lifetime − 1 s) ago and (lifetime + 1 s) ago | The first is valid; the second raises `TokenExpiredError` | The exact expiry boundary |
| TOK-L2 | Change `ACCESS_TOKEN_EXPIRE_MINUTES` | The token lifetime follows the setting | The lifetime must not be hard-coded |
| TOK-L3 **(AI)** | Token issued in the same second as a password change, and one second earlier | The first is valid; the second gets 401 `session_revoked` | `iat` is in whole seconds: a known, accepted limit of AUTH-03 |
| TOK-X1 | Expired token in `get_current_user` | 401 `token_expired`, distinct from `invalid_token` | The backoffice shows "your session expired" only for this code |
| TOK-X2 | Malformed or empty token, wrong signature, missing `sub` or empty `sub` | 401 `invalid_token` | Tampered input |
| TOK-X3 **(AI)** | Token with `"alg": "none"` | 401 `invalid_token` | A classic JWT attack: accepting an unsigned token |
| TOK-X4 | Password reset token used as a session | 401 `invalid_token` | An email link must not open a session |
| TOK-X5 | No token | 401 `not_authenticated` | |
| TOK-X6 | Token of a deleted user, of a deactivated account, and issued before a password change | 401 `invalid_token`, 403 `inactive_user` and 401 `session_revoked` | A valid signature isn't enough: the account's current state wins |

### `test_login.py` — `POST /auth/login`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| LOG-F1 | Correct email and password | A valid token whose `sub` is the user | |
| LOG-L1 | Email with uppercase letters and surrounding spaces | Finds the same user | The email is stored normalized |
| LOG-L2 | Empty email or password | Rejected by the `LoginRequest` rule | The ticket's "empty field" |
| LOG-L3 **(AI)** | Password longer than 72 bytes | 401 `invalid_credentials`, no internal error | bcrypt rejects such passwords; `verify_password` must return `False` |
| LOG-X1 | Wrong password and unknown email | The same 401 `invalid_credentials` in both cases | Don't reveal which emails are registered |
| LOG-X2 | Deactivated account with the correct password | 403 `inactive_user` and no token | |
| LOG-X3 **(AI)** | Deactivated account with a wrong password | 401 `invalid_credentials`, not 403 | Without the password, don't reveal that the account exists and is deactivated |

### `test_me.py` — `GET /auth/me`

| ID | Case | Expected decision |
|---|---|---|
| ME-F1 | User with a profile | ID, email, role and profile of the token's user |
| ME-L1 | User without a profile | Empty `profile`, no error |
| ME-X1 | Token of a deleted user | Never reaches the route: 401 `invalid_token` |

### `test_forgot_password.py` — `POST /auth/forgot-password`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| FGT-F1 | Email of an active account | Creates the link (expires after `PASSWORD_RESET_EXPIRE_MINUTES`) and schedules an email to the user with their name and a link carrying the token | |
| FGT-L1 | Fourth request within an hour, and another one after the hour | The fourth creates no link and no email; after the hour, it does | Limit of 3 per hour (P-9 in AUTH-03) |
| FGT-L2 | Email in uppercase; user without a profile | Finds the account; the email goes out without a name | |
| FGT-X1 | Unknown email and deactivated account | No link and no email, and **the same message** as in FGT-F1 | Don't reveal which accounts exist |

### `test_validate_reset_token.py` — `POST /auth/reset-password/validate`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| VAL-F1 | Valid link | Accepted and **not consumed**: it can still be used to reset afterwards | It only checks |
| VAL-L1 | One second before expiry and at the exact instant | The first is valid; the second gets `reset_token_expired` | Boundary: the database treats it as expired at that same instant (`expires_at <= now`) |
| VAL-X1 | Used link; text that isn't a token; an access token instead | `reset_token_used`; `invalid_reset_token`; `invalid_reset_token` | |
| VAL-X2 **(AI)** | Token carrying the `jti` of another user's link | `invalid_reset_token` | The link must belong to the token's user |
| VAL-X3 | User deactivated or deleted after requesting the link | `invalid_reset_token` | |

### `test_reset_password.py` — `POST /auth/reset-password`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| RST-F1 | Valid link and a new password | The new password works and the old one doesn't; the link is marked used; `password_changed_at` is stored and earlier sessions get `session_revoked` | |
| RST-L1 | Two pending links; one is used | The other is voided too | |
| RST-L2 | New password of 8 characters and of 72 bytes; of 7 characters and of 73 bytes (with accented letters) | The first two are accepted; the last two aren't | Same rules as registration; accented letters take 2 bytes |
| RST-X1 | Used, expired or invalid link | Its code (`reset_token_used`, `reset_token_expired`, `invalid_reset_token`) and **the password doesn't change** | A failure never leaves the account half-changed |

### `test_change_password.py` — `POST /auth/change-password`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| CHG-F1 | Correct current password | Stores the new one; the returned token is valid and the previous one gets `session_revoked`; pending links are voided | |
| CHG-L1 | New password equal to the current one | Accepted, and sessions are revoked | Documents the current decision: no rule forbids it |
| CHG-L2 | Empty current password; new password of 7 characters | Rejected by the `ChangePasswordRequest` rules | |
| CHG-X1 | Wrong current password | 400 `invalid_current_password`; the password, sessions and links stay unchanged | |
| CHG-X2 | The account is deleted between authentication and the change | 401 `invalid_token`, as `get_current_user` answers for a deleted user | Regression test for bug H-2 (see "Bugs found") |

### `test_register.py` — `POST /users`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| REG-F1 | Valid data with a profile | An active `user`, lowercase email, password stored only as a verifiable bcrypt hash; profile with the data sent | |
| REG-L1 | No profile data | Profile created with empty fields | Every user always has a profile |
| REG-L2 | Password of 8 characters and of 72 bytes; of 7 and of 73 bytes | The first are accepted; the others aren't | |
| REG-L3 | Email already registered, with different case or with spaces | 409 `duplicate_email` and nothing is created | The ticket's "duplicate user" |
| REG-X1 | `role: admin` is sent | Rejected by the model (field not allowed) | Nobody can register as an admin |
| REG-X2 | Badly formatted email | Rejected by the model | |
| REG-X3 | Profile creation fails | The user isn't kept | No profile, no user |

### `test_list_users.py` — `GET /users`

| ID | Case | Expected decision |
|---|---|---|
| LST-F1 | An admin lists users | All accounts, without password hashes |
| LST-L1 | Only the admin exists | A single account |
| LST-X1 | A `user` or a `manager` asks | 403 `forbidden` |

### `test_get_user.py` — `GET /users/{id}`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| GET-F1 | A user asks for their own account; an admin asks for another | The data, without the hash | |
| GET-L1 | An admin asks for an ID that doesn't exist | 404 `user_not_found` | |
| GET-X1 | A user asks for another account, whether it exists or not | 403 in both cases | The 403 comes before the lookup: it doesn't reveal whether the ID exists |

### `test_update_user.py` — `PUT /users/{id}`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| UPD-F1 | A user changes their email and password; an admin changes another user's role and status | Saved; the password as a hash | |
| UPD-L1 | Change to one's own email; change to another account's email with different case | The first is accepted; the second gets 409 `duplicate_email` | |
| UPD-L2 | Empty body or fields set to `null` | Rejected by `UserUpdate` | |
| UPD-X1 | A `user` or a `manager` tries to change `role` or `is_active`, even on their own account | 403 and nothing changes | Privilege escalation |
| UPD-X2 | A user edits another account; an admin edits an ID that doesn't exist | 403 and 404 | |
| UPD-X3 **(AI)** | A user changes their password through this route | **To be checked:** are earlier sessions ended, as in AUTH-03? | See hypothesis H-1 |

### `test_delete_user.py` — `DELETE /users/{id}`

| ID | Case | Expected decision |
|---|---|---|
| DEL-F1 | A user deletes their account | The user, their profile and their password reset links are deleted; their token stops working |
| DEL-L1 | An admin deletes another account | Deleted |
| DEL-X1 | A user tries to delete another account; an admin deletes an ID that doesn't exist | 403 with nothing deleted; 404 |

### `test_get_my_profile.py` — `GET /profiles/me`

| ID | Case | Expected decision |
|---|---|---|
| PME-F1 | User with a profile | Their profile |
| PME-L1 | Profile with all fields empty | The profile, with empty fields |
| PME-X1 | User whose profile doesn't exist | 404 `profile_not_found` |

### `test_update_my_profile.py` — `PUT /profiles/me`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| UPM-F1 | Only the phone is sent | The phone changes; everything else stays | Partial update |
| UPM-L1 | `null` in a field; text with surrounding spaces; maximum lengths (120, 30 and 200) and one more | Clears the field; trims; accepts the maximum and rejects the next | |
| UPM-X1 | Empty body, unknown field, or a name made only of spaces | Rejected by `ProfileUpdate` | |
| UPM-X2 | User without a profile | 404 `profile_not_found` | |

### `test_get_profile.py` — `GET /profiles/{user_id}`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| GPR-F1 | The owner asks; an admin asks for another | The profile | |
| GPR-L1 **(AI)** | A `manager` asks for another profile | 403 | A `manager` isn't an admin |
| GPR-X1 | A user asks for another profile; an admin asks for one that doesn't exist | 403 and 404 | |

### `test_update_profile.py` — `PUT /profiles/{user_id}`

| ID | Case | Expected decision | Why |
|---|---|---|---|
| UPR-F1 | The owner updates their profile by ID | Saved | |
| UPR-L1 | An admin tries to update another profile | 403 | AUTH-01 rule: only the owner edits their profile, even against an admin |
| UPR-X1 | A user tries to update another profile; the owner has no profile | 403 with no changes; 404 | |

## AI-assisted review

With the draft cases done, a dedicated pass was made with the AI agent (Claude Code): review the logic in `core/security.py`, `auth/passwords.py`, `auth/dependencies.py`, `users/service.py` and the routers, and suggest missing cases. The developer reviewed each suggestion before including it.

**Cases it suggested that were added (marked AI):**
- TOK-L3 (revocation in the same second);
- TOK-X3 (`alg: none`);
- LOG-L3 (password longer than 72 bytes);
- LOG-X3 (deactivated account with a wrong password);
- VAL-X2 (another user's link);
- UPD-X3 (password change through `PUT /users/{id}`);
- GPR-L1 (`manager` versus admin).

**Possible bugs it pointed out.** If a test confirms one, it will be discussed before fixing it and recorded under "Bugs found".

- **H-1. `PUT /users/{id}` with `password` doesn't end earlier sessions.** `users/service.py` (`update_user`) stores the new hash, but doesn't set `password_changed_at` and doesn't void pending password reset links. `change-password` and `reset-password` do both. If confirmed, someone changing their password through this route to lock out an intruder wouldn't succeed.
- **H-2. Misleading error in `change-password` if the account is deleted during the change.** `passwords.change_password` answers "the current password is incorrect" (400) and voids the links before checking that the user still exists. It needs a race between requests: unlikely, but the message would be false. **Confirmed and fixed** (see "Bugs found").

## Bugs found

### H-2. `change-password` claimed a wrong current password when the account no longer existed

- **Status:** fixed on 2026-11-10, with the developer's approval.
- **How it was found:** hypothesis from the AI-assisted review, confirmed with a manual probe on a temporary database: with the correct current password, deleting the account between authentication (`get_current_user`) and the change made the API answer 400 `invalid_current_password`.
- **Cause:** `passwords.change_password` read a failed update (`None`, because the user no longer exists) as a wrong password. It also voided the reset links before checking it.
- **Fix:** a new `AccountGoneError` exception, raised inside the lock before touching the links. The route maps it to 401 `invalid_token`, which is what `get_current_user` answers for a deleted user's token; the backoffice closes the session on a 401. A wrong current password is still 400 `invalid_current_password`.
- **Regression test:** CHG-X2 (`tests/auth/test_change_password.py`). It fails without the fix and passes with it.
- **Impact:** low. It needs two requests to coincide (deleting the account and changing its password), but the message was false and could lead someone to retry a password that was correct.

## Coverage

*Pending.* Baseline coverage of the authentication modules (`core/security.py`, `domains/auth`, `domains/users` and `domains/profiles`), measured on 2026-11-10:

| Suite | Coverage |
|---|---|
| Full (`uv run pytest --cov`) | 98 % |
| Without HTTP tests | 75 % |

AUTH-088's target is 70 % or more **with `tests/auth/` alone**.
