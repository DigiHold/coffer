"""Applies the raw SQL revisions to the database named by DATABASE_URL."""

import os

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# NullPool closes the connection on exit instead of keeping it for later reuse.
engine = create_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
