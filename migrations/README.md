# Database schema lifecycle

The current SQLAlchemy store can create the initial schema for local SQLite and first-run development environments.

Before production rollout, generate and review an Alembic baseline from `ukb.storage.orm.Base`, then run migrations as a separate deployment step before starting the API.

Do not allow application startup to perform destructive migrations.
