from dataclasses import dataclass
from decimal import Decimal

from coffer.models import db
from coffer.provider import MockPaymentProvider


@dataclass(frozen=True)
class Charge:
    token: str
    amount: Decimal
    currency: str
    idempotency_key: str
    in_transaction: bool


class SpyProvider(MockPaymentProvider):
    """The mock provider, recording each charge and whether a transaction was open."""

    def __init__(self) -> None:
        self.charges: list[Charge] = []

    def charge(
        self, token: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> str:
        in_transaction = db.session().in_transaction()
        self.charges.append(
            Charge(token, amount, currency, idempotency_key, in_transaction)
        )
        return super().charge(token, amount, currency, idempotency_key)
