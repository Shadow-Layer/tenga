# POS payment and fiscal adapter configuration

This note describes the server-side adapter contract added for the POS workstream.
It is not a statement of live Paynow or ZIMRA certification. The repository has no
provider credentials, production callback validation, or certified TengaVFD endpoint.

Every sale requires an active `till_session_id` owned by the authenticated assigned
operator and a stable `Idempotency-Key` (or matching request field). Cash replay with
the same key and payload returns the original sale; reusing a key with a different
payload is a conflict. The authenticated offline `SALE_COMMIT` sync operation also
validates the original open session and operator.

The browser stores an unresolved cash request in IndexedDB before sending it. Offline
cash checkout uses the last cached product/tax catalog and verified till session, and
remains unconfirmed on the device until the authenticated server accepts the exact
request. The request includes its expected total and per-item price/tax snapshots,
which the server verifies against current records. A retry reuses that exact request
and key; a changed price or tax rule is rejected before creating a sale, while
transport-uncertain outcomes remain locked for safe retry. The server exposes
`X-Sale-Outcome: NOT_CREATED` only when it has confirmed that no sale was created.
Do not treat a locally staged sale as completed, hand over goods, or count it as
settled until the server confirms the sale. Paynow cannot be initiated offline.

## Paynow

Set these variables only in the backend deployment secret store:

- `PAYNOW_API_URL`
- `PAYNOW_INTEGRATION_ID`
- `PAYNOW_INTEGRATION_KEY`
- `PAYNOW_CALLBACK_SECRET`
- `PAYNOW_CALLBACK_URL` (public HTTPS URL for `/api/v1/paynow/callback`)
- `PAYNOW_RETURN_URL` (HTTPS checkout return page; its redirect is informational)
- `PAYNOW_TIMEOUT_SECONDS` (optional, defaults to `15`)

The current transport expects a normalized server-to-server adapter API:

- `POST /v1/payments`, receiving merchant reference, server-calculated amount and
  currency, `HOSTED` or `MOBILE_MONEY`, plus callback/return URLs; it returns a
  provider reference and/or HTTPS redirect URL.
- `GET /v1/payments/{merchant_reference}`, returning merchant reference, provider
  reference, amount, currency, and provider status.
- Callback body is JSON with merchant reference, provider reference (when available),
  amount, currency, and status. `X-Paynow-Signature` is the HMAC-SHA256 hex digest
  of the exact raw body, using `PAYNOW_CALLBACK_SECRET`.

The browser return is never a payment proof. Server status verification is mandatory
before settlement. Timeout/unknown initiation results are not initiated again; use
`GET /api/v1/sales/{sale_id}/paynow` to reconcile status and retry only a terminally
failed attempt through `POST /api/v1/paynow/{attempt_id}/retry`. The callback endpoint
is `POST /api/v1/paynow/callback`. Credentials and mobile phone numbers are not stored
in payment-attempt rows.

**Provider activation gate:** confirm the official Paynow Zimbabwe merchant API
contract, authentication/signature algorithm, response field mapping, sandbox tests,
callback reachability, settlement reconciliation, and supported mobile-money
networks. The normalized endpoint above must be backed by a verified provider adapter;
do not point it directly at a provider URL unless that contract has been validated.

## TengaVFD fiscal boundary

Set these variables only in the backend deployment secret store:

- `TENGAVFD_API_URL`
- `TENGAVFD_API_TOKEN`
- `TENGAVFD_DEVICE_ID`
- `TENGAVFD_TIMEOUT_SECONDS` (optional, defaults to `20`)

The adapter contract accepts `POST /v1/submissions` with an immutable request
reference and server-generated receipt payload, and
`GET /v1/submissions/{request_reference}` for reconciliation. The submit operation
includes the request reference as an idempotency key. Acknowledged status and fiscal
numbers are accepted only from the remote response; missing or ambiguous results stay
uncertain. Fiscal state does not change payment, sale, or stock state.

**Fiscal activation gate:** supply and certify the real TengaVFD implementation,
device credentials, ZIMRA/device approval evidence, response/signature mapping,
connectivity/recovery procedures, and compliance tests. Do not claim production
Zimbabwe fiscal compliance until those gates pass.

## Safe local tests

Use mock adapter transports; never add credentials to source, request payloads,
database records, or logs. Tests cover pending initiation, timeout recovery, signed
callback plus remote verification, settlement idempotency, fiscal uncertainty, and
reconciliation without requiring external credentials.
