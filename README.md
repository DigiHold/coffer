# Coffer

Coffer is the payment service of an online shop. It exposes one HTTP endpoint that charges the user's saved card for a cart, and the PostgreSQL schema that records every payment attempt. It is built with Flask, SQLAlchemy and PostgreSQL, and the payment provider is a mock.

## Run it

You need Docker with the Compose plugin (`docker compose`) and `make`. Python and PostgreSQL run in containers, so nothing else gets installed. On a Mac with Colima, run `colima start` first.

```bash
make up      # build, migrate, load the demo data, serve the API on http://localhost:8000
make demo    # reset the demo data and pay every demo cart, expected and actual status side by side
make check   # lint, format, strict types, migrations down and up, tests with coverage
make test    # the tests only
make psql    # a psql shell on the demo database, to look at the payments table
make down    # stop everything and delete the data
```

`make up` needs no setup file. The database port stays inside Docker, and the API listens on port 8000.

The same commands without `make`:

| Target | Command |
|---|---|
| `up` | `docker compose up --build --detach --wait db api`, then the `demo` seed command |
| `demo` | `docker compose exec -T db psql --quiet -v ON_ERROR_STOP=1 --username=coffer --dbname=coffer < db/seed.sql`, then `scripts/demo.sh` |
| `check` | `docker compose run --rm --build dev scripts/check.sh` |
| `test` | `docker compose run --rm --build dev pytest` |
| `psql` | `docker compose exec db psql --username=coffer --dbname=coffer` |
| `down` | `docker compose --profile dev down --volumes` |

### Pay a cart with curl

After `make up`, mint a token for Alice and pay her cart from the task's sample data:

```bash
TOKEN=$(docker compose exec -T api flask issue-token alice@example.com)
curl -i -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/carts/c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1/payments
```

The answer is `201 Created` with the payment:

```json
{
  "amount": "70.00",
  "cart_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "created_at": "2026-11-02T14:42:41.083569+00:00",
  "currency": "USD",
  "id": "6e0a2025-b04c-49d8-9df8-5237d15d0bba",
  "status": "succeeded"
}
```

The same request again answers `409 cart_not_active`, because the cart is checked out, and `make demo` resets the data.

## The endpoint

`POST /carts/{cart_id}/payments` takes an `Authorization: Bearer <token>` header and no body. The token names the user, and the amount comes from the total calculation service. The card is the user's default saved card. Money is a string in JSON, so no client reads it as a float.

| Situation | Status | `error.code` |
|---|---|---|
| The card was charged, the cart is checked out | 201 | (the payment) |
| The card was declined | 402 | `card_declined`, with `payment_id` |
| The provider is down and charged nothing | 502 | `provider_unavailable`, with `payment_id` |
| Missing, malformed, expired or badly signed token, or unknown user | 401 | `unauthorized` |
| The cart does not exist or belongs to someone else | 404 | `cart_not_found` |
| The cart id is not a UUID | 404 | `not_found` |
| The cart is checked out or abandoned | 409 | `cart_not_active` |
| Another payment of this cart is in progress | 409 | `payment_in_progress` |
| The cart has no items, or a total of zero | 422 | `nothing_to_pay` |
| The user has no default card | 422 | `no_payment_method` |

Every error has the same shape, `{"error": {"code": "...", "message": "..."}}`, including Flask's own 404, 405 and 500. A 500 never shows the exception, which goes to the log. The contract is also in [openapi.yaml](openapi.yaml).

## How a payment runs

`start_payment` in [coffer/payments.py](coffer/payments.py) works in three steps:

1. One short transaction loads the cart by id and owner, checks that it is active, picks the default card, asks for the total, then commits a `pending` payment with the amount and currency.
2. The provider is called with no transaction open, so a slow provider holds no lock and no busy connection. The payment id is the idempotency key, so a real provider charges at most once per payment.
3. One transaction records the outcome. On success the payment becomes `succeeded` with the provider's charge id, and the cart becomes `checked_out` in the same commit. On a failure the payment becomes `failed` with the reason, and the cart stays active for a retry.

Each outcome writes one INFO log line with the payment id, the cart id and the outcome. The card token never appears in a response or in a log line, and a test checks both.

Neither a double click nor two requests at the same time can charge the card twice. Only one request per cart can insert its `pending` row. The database refuses the others, and the API answers them `409 payment_in_progress`. A test holds the first charge inside the provider while a second request arrives, and checks that the provider was called once.

If the provider call fails in any other way, such as a timeout, or the process dies before step 3, nobody knows whether the card was charged, so the payment stays `pending`. The API answers 500, and the cart answers `409 payment_in_progress` until a reconciliation job asks the provider about it by idempotency key. A second charge stays impossible while the outcome is unknown.

## The payments schema

[migrations/versions/0002_payments.py](migrations/versions/0002_payments.py) adds one table, in the style of the base schema: UUID keys, `NUMERIC(12, 2)` with a `CHAR(3)` currency, a `TEXT` status with a `CHECK` list, and an index on each foreign key.

- One row per attempt. A failed attempt stays as history and a retry adds a new row.
- `amount` and `currency` keep what was charged, even if the cart changes later.
- `payment_method_id` records which saved card was used. The token itself is never copied.
- `provider_reference` is the provider's charge id. It is unique and required once the payment succeeded, and a failed payment requires a `failure_reason`.
- Deleting a cart or a card that has payments fails, because the foreign keys have no cascade and payments are financial records. A card service would soft delete a used card.
- The partial unique index `uq_payments_cart_open` allows one `pending` or `succeeded` payment per cart, and leaves failed ones out so the cart can be paid again. It is the double charge guard.

The rules live in the schema, so they hold for any code that writes to it, and the schema tests prove each one.

## The mock provider

[coffer/provider.py](coffer/provider.py) decides from the card token, so tests and the demo are predictable:

- a token containing `decline` is declined (402),
- a token containing `unavailable` finds the provider down (502),
- any other token is charged and gets a reference like `mock_ch_<hex>`.

`ProviderUnavailableError` means the provider confirmed it charged nothing, as with a refused connection, so the cart can be paid again. An ambiguous outcome such as a timeout after the request left must not raise it, and that payment would stay `pending` for reconciliation. The mock never produces that case.

## Assumptions

- The total calculation service already exists. [coffer/totals.py](coffer/totals.py) has a stand-in that sums `unit_price * quantity` over the cart items, so the price stays the one at which the item was added. A cart holds one currency, the one of its products (every sample product is USD), and a cart that mixes currencies raises an error instead of adding them up. The real service returns amounts with two decimals, like the `NUMERIC(12, 2)` columns.
- The user pays with their default card. Nothing in the base schema prevents two default cards, so the newest one wins. A user without a default card cannot pay.
- Only an `active` cart can be paid. A successful payment moves it to `checked_out`, as the base schema's comment says.
- Authentication belongs to the shop. Here it is a JWT signed with HS256, with the user id as subject, valid for one hour, minted by `flask issue-token <email>`. The user must still exist.
- Another user's cart answers exactly like a missing cart, so the API never reveals which carts exist.
- The base tables stay as given. Their comment says one cart is active at a time, nothing enforces it, and the endpoint does not depend on it.
- The amount goes to the provider as a decimal in major units. A real provider client would convert it to minor units.
- The demo data is not a migration, because demo rows must never reach a production database. [db/seed.sql](db/seed.sql) holds the task's sample data and one user per demo scenario.

## Decisions

- Migrations are raw SQL run by Alembic. The schema is a deliverable, so it reads as SQL, and Alembic still gives versions and downgrades. Migration `0001` is the task's base schema with its comments, and `0002` adds the payments.
- A unique index guards against a double charge, rather than a row lock or a table of idempotency keys. It works across workers and holds no lock during the provider call, and there is no race between a check and an insert because there is no separate check.
- The session keeps loaded values after a commit (`expire_on_commit=False`). Reading the payment or the card after the first commit then opens no transaction for the whole provider call, and a test checks that none is open during the call.
- A declined card answers 402 Payment Required, which tells the client that the payment itself failed and another card may work. A provider outage answers 502 Bad Gateway, which tells the client that a service behind the API failed and nothing was charged.
- The tests run on real PostgreSQL, the database the migrations are written for, so they prove the partial index and its locking as they behave in production. They use their own server, `test-db`, which keeps its data in memory and never touches the demo data. It is migrated once per session and emptied before each test.
- The images run Python 3.15.2, the latest stable release, and every dependency ships wheels for it.

## Security

- The signing key comes from the environment, and the app refuses to start without a database URL or with a key shorter than 32 bytes (RFC 7518 asks for at least the hash size for HS256).
- The algorithm is pinned to HS256, so a token cannot choose its own, `none` included. `exp` and `sub` are required.
- The cart query filters on the owner. Every query binds its parameters, and no SQL is built from input.
- The API image runs as a non root user. The database port is not published. The passwords and the key in `docker-compose.yml` are labelled development only defaults, and a real deployment sets `POSTGRES_PASSWORD` and `JWT_SECRET`.

## Performance

Each lookup is one indexed query, and SQLAlchemy keeps a pool of connections for the short transactions. Gunicorn runs 2 workers with 4 threads each, because each request waits on the provider. At a larger scale the provider call would move to a queue with webhooks for the result, and reads could go to replicas.

## Out of scope

- Stock reservation, which the inventory service owns.
- 3D Secure and provider webhooks, which a real provider adds.
- The reconciliation job for payments left `pending`.
- Refunds, which are a separate endpoint and a separate record.
- Rate limiting, usually done at the API gateway.
- Blocking cart edits while a payment is pending. The cart service can check for a pending payment.

## Project layout

```
coffer/
  __init__.py      create_app(): config, database, error handlers, routes, CLI
  config.py        settings from the environment, checked at start
  models.py        SQLAlchemy mappings of the columns the code uses
  auth.py          JWT bearer authentication and the issue-token command
  errors.py        ApiError and the JSON error handlers
  routes.py        POST /carts/<cart_id>/payments
  payments.py      start_payment(), the three steps
  provider.py      PaymentProvider interface and the mock
  totals.py        TotalCalculator interface and the stand-in
migrations/        Alembic environment and the two SQL revisions
db/seed.sql        demo data
scripts/check.sh   every quality gate, run by make check and CI
scripts/demo.sh    the demo scenarios with curl
tests/             endpoint, concurrency, schema and unit tests
openapi.yaml       the endpoint contract
```

## Versions

Every version was the latest stable release on 2026-11-02. They are pinned in [pyproject.toml](pyproject.toml) and locked with uv in `uv.lock`, and the images are `python:3.15.2-slim-trixie` and `postgres:18.6-trixie`. CI runs `make check`, `make up` and `make demo`.
