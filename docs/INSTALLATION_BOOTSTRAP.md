# First-Install Organization and Owner Bootstrap

This procedure applies only to a **fresh, empty database**. It creates one local
organization and its first local administrator. It does not create or validate a
license. Central registration and licensing are deferred to a separate SRS after
POS completion.

## Configure the operator secret

Generate a distinct 32-byte secret for this installation with a cryptographically
secure generator, for example:

```sh
python -c 'import secrets; print(secrets.token_hex(32))'
```

Inject the generated value as `INITIAL_SETUP_SECRET` through the deployment's
protected server-side secret mechanism (for Compose, the operator's uncommitted
environment file or secret store). Do not reuse it across installations,
commit it, put it in a URL, or include it in request logs or shell history.
Avoid putting the literal secret in command arguments; load it into the
operator's protected environment instead.

The Compose API port is bound to `127.0.0.1`; it is not directly reachable from
other network hosts. The public Nginx frontend returns `404` for the bootstrap
path. Run the operator request on the deployment host via loopback, or use an
SSH local port forward to that host; do not send the setup secret through the
public HTTP frontend. Other production reverse-proxy arrangements must preserve
this operator-only network boundary.

Remove `INITIAL_SETUP_SECRET` from the deployment configuration after
initialization succeeds.

The endpoint is unavailable when the secret is unset or shorter than 32
characters. The secret authorizes only this one-time setup; it does not
authenticate subsequent POS requests.

## Initialize

After the database schema has been installed, send a request to
`http://127.0.0.1:${API_PORT:-8000}/api/v1/organizations/bootstrap` from the
deployment host. Obtain the secret from the protected secret store into a
non-echoing shell variable, then send it through curl's standard input config
rather than placing its value in shell history or the process argument list:

```sh
read -r -s -p 'Setup secret: ' INITIAL_SETUP_SECRET
printf '\n'
curl --config - <<EOF
url = "http://127.0.0.1:${API_PORT:-8000}/api/v1/organizations/bootstrap"
request = "POST"
header = "X-Setup-Secret: ${INITIAL_SETUP_SECRET}"
header = "Content-Type: application/json"
fail-with-body
data = "{\"organization\":{\"name\":\"Example Store\",\"code\":\"EXAMPLE\"},\"owner\":{\"username\":\"owner\",\"email\":\"owner@example.test\",\"password\":\"REPLACE_WITH_A_SECURE_PASSWORD\"}}"
EOF
request_status=$?
unset INITIAL_SETUP_SECRET
if [ "$request_status" -ne 0 ]; then exit "$request_status"; fi
```

Replace the example organization and owner values before sending. Use a
password of at least eight characters and at most 72 UTF-8 bytes, matching the
current bcrypt implementation.

The first owner is assigned the local `admin` role. Verify the response contains
the new organization and owner identifiers, then authenticate through the
regular local login endpoint using the owner credentials. The password is stored
as a bcrypt hash; neither the password nor setup secret is returned by the endpoint.
Organization and owner creation commit in one transaction. Database locking
serializes concurrent setup attempts; after success, replay is rejected.

The legacy unauthenticated `POST /api/v1/organizations` endpoint returns `410
Gone`. Organization setup must not create an ownerless tenant.

## Existing databases and recovery

If any application data already exists, bootstrap returns `409 Conflict`
without changing the database. Existing installations are not migrated,
discarded, merged, or reassigned by this feature. This endpoint provides no
post-setup reset or owner-recovery path; recovery requires a separately approved
procedure. For an empty installation where the secret is lost before setup,
rotate the deployment secret through the operator's secret-management process.
If organization or owner creation fails before commit, the transaction rolls
back and leaves the installation eligible for a retry with the configured
secret. After a successful setup, reset and owner recovery are explicitly
unsupported by this procedure; do not clear application data to retry.

## Future licensing boundary

The customer installation owns POS operational records locally. No local license
generation, cloud endpoint, signature format, expiry, offline grace, revocation,
installation identity, or recovery protocol is introduced here. Those decisions
belong to the future central-platform SRS.
