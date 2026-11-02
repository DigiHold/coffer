"""Payments: one row per attempt to charge the card for a cart."""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.execute("""
-- One row per attempt. No cascade: payments are financial records.
CREATE TABLE payments (
    id                 UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id            UUID           NOT NULL REFERENCES carts(id),
    payment_method_id  UUID           NOT NULL REFERENCES user_payment_methods(id),
    amount             NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency           CHAR(3)        NOT NULL,
    status             TEXT           NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'succeeded', 'failed')),
    provider_reference TEXT           UNIQUE,
    failure_reason     TEXT,
    created_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT payments_succeeded_has_reference
        CHECK (status <> 'succeeded' OR provider_reference IS NOT NULL),
    CONSTRAINT payments_reason_only_when_failed
        CHECK ((status = 'failed') = (failure_reason IS NOT NULL))
);

CREATE INDEX idx_payments_cart_id ON payments(cart_id);
CREATE INDEX idx_payments_payment_method_id ON payments(payment_method_id);

-- One pending or succeeded payment per cart: the double charge guard.
CREATE UNIQUE INDEX uq_payments_cart_open
    ON payments(cart_id) WHERE status IN ('pending', 'succeeded');
""")


def downgrade() -> None:
    op.execute("DROP TABLE payments")
