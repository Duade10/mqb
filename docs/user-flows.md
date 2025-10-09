# End-to-End User Flows & Backend Contract

This guide expands the guest-facing journey and documents the administrator experience from bootstrap to day-to-day content management. Each section lists the expected sequence of front-end actions, the HTTP requests that support them, and important response or error semantics.

---

## 0. Platform Bootstrap (one-time)

Used to seed the very first administrator account.

1. **Prepare environment secrets**
   - Configure `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in the runtime environment. Requests are rejected unless both values are present and the password meets policy requirements (`>=12` chars with upper/lowercase, number, symbol).

2. **Create the super admin**
   - `POST /admin/auth/bootstrap`
   - Response: `{ "email": "..." }` confirming the stored account.
   - Failure modes:
     - `400 Bootstrap already completed` once any admin exists.
     - `400 Bootstrap credentials not configured` when env vars are missing.
     - `400 Password does not meet the required complexity policy.` when the configured password is weak.

All subsequent admin APIs require an authenticated user and cannot be called until bootstrap completes.

---

## 1. Guest Journey (public APIs)

### 1.1 Pre-flight readiness
- Optional: `GET /health` to surface availability in monitoring or gate application boot.

### 1.2 Listing resolution from QR scan
1. Browser opens the QR deep link `https://.../q/{token}`.
2. `GET /q/{token}` validates the JWT, ensures it contains `listing_id`, and checks that the listing exists.
3. On success, the backend issues `307 Temporary Redirect` to the SPA route `/public/listings/{listing_id}` so the front end can render with that ID in scope.
4. Error handling:
   - `400 Invalid token` or `400 Invalid token payload` when decoding fails.
   - `404 Listing not found` if the listing is missing.

### 1.3 Consent template loading
1. Upon landing on `/public/listings/{listing_id}`, call `GET /public/listings/{listing_id}/consent?language={code}`.
2. The handler resolves the most recent published template and attempts to return the requested translation (falls back to English when missing).
3. Response payload:
   ```json
   {
     "template_id": 123,
     "template_version": 4,
     "status": "published",
     "translation": {
       "language_code": "es",
       "title": "...",
       "body": "..."
     }
   }
   ```
4. Error conditions:
   - `404 Listing not found` when the context is invalid.
   - `404 Consent template not found` when no published version exists.
   - `404 Consent translation not found` if neither the requested nor English translation is stored.

### 1.4 Consent submission
1. When the guest acts, `POST /public/listings/{listing_id}/consent` with body:
   ```json
   {
     "template_id": 123,
     "template_version": 4,
     "language_code": "es",
     "decision": "accept" | "decline"
   }
   ```
2. The API validates that the submitted template matches the current published version, captures IP address and `User-Agent`, and persists the log.
3. Success returns the stored record with `id`, `template_version`, `decision`, `language_code`, and `created_at` fields.
4. Error handling:
   - `400 Invalid template` when the template ID does not match the latest published draft.
   - `409 Template version is stale` when the client is behind—re-fetch the template and re-render.

### 1.5 In-stay guide (FAQs & tutorials)
1. Load FAQs: `GET /public/listings/{listing_id}/faqs?language={code}`
   - Only FAQs marked active are returned. The backend will fall back to English per item when a translation is missing.
   - Response:
     ```json
     {"items": [{"id": 1, "question": "...", "answer": "...", "language_code": "es"}]}
     ```
2. Load tutorials: `GET /public/listings/{listing_id}/tutorials?language={code}`
   - Same fallback behavior; only active tutorials are included.
   - Response:
     ```json
     {
       "items": [
         {
           "id": 10,
           "title": "...",
           "description": "...",
           "video_url": "https://...",
           "thumbnail_url": "https://...",
           "language_code": "es"
         }
       ]
     }
     ```
3. Shared errors: `404 Listing not found` if the listing context is invalid.

---

## 2. Administrator Journey

### 2.1 Authentication lifecycle

1. **Login**
   - `POST /admin/auth/login`
   - Accepts either JSON or form payload `{ email, password, totp_code?, recovery_code? }`.
   - For TOTP-enabled accounts, the client must supply a valid code (or an unused recovery code) in addition to the password.
   - Success response:
     ```json
     {
       "access_token": "...",
       "refresh_token": "...",
       "expires_in": 3600
     }
     ```
   - Errors include `401 Invalid credentials`, `400 2FA code required`, and `401 Invalid 2FA code` variants.

2. **Token refresh**
   - `POST /admin/auth/refresh` with `{ "refresh_token": "..." }`.
   - Rotates the refresh family; previous refresh token is revoked and replaced.
   - Errors: `401 Invalid refresh token` or `401 Refresh token expired or revoked` (also revokes the entire family).

3. **Logout**
   - `POST /admin/auth/logout` with `{ "refresh_token": "..." }` to revoke the refresh family server-side.

4. **Profile fetch**
   - `GET /admin/me` returns the authenticated admin’s profile for session bootstrap within the SPA.

5. **Password reset workflow**
   - Request: `POST /admin/auth/request-password-reset` with `{ "email": "..." }`; emits an audit log containing the raw reset token for QA/testing environments.
   - Reset: `POST /admin/auth/reset-password` with `{ "token": "...", "password": "newStrongPass" }`. Revokes all active refresh tokens on success.

6. **Two-factor authentication (optional)**
   - Setup secret: `POST /admin/auth/2fa/setup` → `{ "secret": "...", "uri": "otpauth://..." }`.
   - Enable: `POST /admin/auth/2fa/enable` with `{ "totp_code": "123456" }` returns fresh recovery codes.
   - Disable: `POST /admin/auth/2fa/disable` with either `{ "totp_code": "..." }` or `{ "recovery_code": "..." }`.

### 2.2 Admin user management

1. **Invite flow**
   - Create invite: `POST /admin/invites` with `{ "email": "new@mrhost.com", "expires_in_hours"? }` (admins or superadmins only). Returns `{ "code": "...", "expires_at": "..." }`.
   - Accept invite: `POST /admin/auth/register` with `{ "invite_code", "email", "password" }` to create the account and mark the invite used.

2. **List/update admins**
   - `GET /admin/users` (admins/superadmins only) returns all admin profiles.
   - `PUT /admin/users/{user_id}` with payload like `{ "role": "manager", "is_active": false }` to adjust roles or deactivate accounts.

### 2.3 Listing and content management

1. **Listings CRUD**
   - `POST /admin/listings` to create (`{ "name", "slug" }`).
   - `GET /admin/listings` / `GET /admin/listings/{id}` to browse.
   - `PUT /admin/listings/{id}` to rename or update slug.
   - `DELETE /admin/listings/{id}` to remove (fails with `404` if not found).

2. **QR tokens**
   - `POST /admin/listings/{listing_id}/qr` to mint a signed JWT for embedding in printed codes.

3. **Consent templates**
   - Create new version: `POST /admin/listings/{listing_id}/consent-templates` with translations array; auto-increments version and starts in `draft` status.
   - Update/publish: `PUT /admin/consent-templates/{template_id}` to adjust translations or change `status` to `published` (sets `published_at`).
   - List history: `GET /admin/listings/{listing_id}/consent-templates` ordered by newest version first.

4. **FAQs**
   - `POST /admin/faqs` to create (includes `listing_id`, `is_active`, and translations).
   - `PUT /admin/faqs/{faq_id}` to toggle active flag or replace translation set.
   - `GET /admin/listings/{listing_id}/faqs` to review.
   - `DELETE /admin/faqs/{faq_id}` to remove.

5. **Tutorials**
   - `POST /admin/tutorials`, `PUT /admin/tutorials/{id}`, `GET /admin/listings/{listing_id}/tutorials`, `DELETE /admin/tutorials/{id}` with similar semantics to FAQs but translation entries include `title`, `description`, `video_url`, and optional `thumbnail_url`.

### 2.4 Audit and reporting

- **Consent logs**
  - `GET /admin/consent-logs` supports filters `listing_id`, `language`, `decision`, `start`, and `end`. Returns each log with the metadata captured during submission (IP, user-agent, timestamp).

These endpoints power the admin dashboard’s reporting views and compliance exports.

---

## 3. Implementation Notes

- Every admin router declares `Depends(get_current_admin)`; the frontend must send the `Authorization: Bearer {access_token}` header with each request.
- Access token expiration is driven by `ACCESS_TOKEN_EXPIRE_MINUTES`; the UI should preemptively call refresh before expiry to avoid 401s.
- When a refresh token is compromised or expires, the backend revokes the entire token family to prevent reuse. Always replace stored refresh tokens after each successful refresh call.
- Translation sync endpoints (`consent-templates`, `faqs`, `tutorials`) treat the submitted set as the source of truth: omitted language codes are deleted from the database.

Use this document as the contract reference when wiring the SPA(s) or automated tests against the backend.
