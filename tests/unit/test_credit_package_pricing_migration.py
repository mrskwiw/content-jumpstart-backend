"""Unit tests for the self-healing credit_packages pricing migration in
backend/database.py::init_db().

Bug context: BILLING-01 (commit 03fbd67, 2026-07-30) locked credit pricing at
$0.50/credit (subscription "package" type) and $1.00/credit (non-expiring
"additional" top-up type), superseding the legacy $2.00/$2.50 rates. The
credit_packages *seed* values were updated, but any instance already
provisioned before that commit kept its legacy-priced rows forever — nothing
ever corrected already-seeded data. Since stripe_service.py charges
`price_usd` directly, this is a real pricing bug, not cosmetic. init_db() now
self-heals: on every boot it recomputes price_usd for any row still sitting
at the exact legacy rate, and leaves everything else (including a
deliberately admin-customized price) untouched.
"""

import uuid

import backend.database
import pytest
from backend.database import Base, init_db
from sqlalchemy import create_engine, text


@pytest.fixture
def temp_db_engine():
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


def _seed_package(engine, *, credits, price_usd, package_type, description=""):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO credit_packages
                (id, name, credits, price_usd, package_type, is_active, description)
                VALUES (:id, :name, :credits, :price_usd, :package_type, TRUE, :description)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": f"{package_type}-{credits}",
                "credits": credits,
                "price_usd": price_usd,
                "package_type": package_type,
                "description": description,
            },
        )


def _run_init_db_against(temp_db_engine):
    original_engine = backend.database.engine
    backend.database.engine = temp_db_engine
    try:
        init_db()
    finally:
        backend.database.engine = original_engine


class TestCreditPackageLegacyRateFix:
    def test_legacy_standard_package_rate_corrected(self, temp_db_engine):
        Base.metadata.create_all(bind=temp_db_engine)
        _seed_package(
            temp_db_engine, credits=100, price_usd=200.0, package_type="package"
        )  # legacy $2.00/credit

        _run_init_db_against(temp_db_engine)

        with temp_db_engine.connect() as conn:
            row = conn.execute(
                text("SELECT price_usd FROM credit_packages WHERE package_type = 'package'")
            ).first()
        assert row.price_usd == pytest.approx(50.0)  # 100 credits * $0.50

    def test_legacy_additional_package_rate_corrected(self, temp_db_engine):
        Base.metadata.create_all(bind=temp_db_engine)
        _seed_package(
            temp_db_engine,
            credits=100,
            price_usd=250.0,  # legacy $2.50/credit
            package_type="additional",
            description="Top-up credits at $2.50 each",
        )

        _run_init_db_against(temp_db_engine)

        with temp_db_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT price_usd, description FROM credit_packages "
                    "WHERE package_type = 'additional'"
                )
            ).first()
        assert row.price_usd == pytest.approx(100.0)  # 100 credits * $1.00
        assert "1.00" in row.description
        assert "2.50" not in row.description

    def test_admin_customized_price_is_not_touched(self, temp_db_engine):
        """A row that doesn't match the exact legacy rate (e.g. an admin gave a
        discount) must be left alone — the fix targets the known legacy value
        only, never a blanket repricing."""
        Base.metadata.create_all(bind=temp_db_engine)
        _seed_package(
            temp_db_engine, credits=100, price_usd=75.0, package_type="package"
        )  # deliberately not $2.00 or $0.50 per credit

        _run_init_db_against(temp_db_engine)

        with temp_db_engine.connect() as conn:
            row = conn.execute(
                text("SELECT price_usd FROM credit_packages WHERE package_type = 'package'")
            ).first()
        assert row.price_usd == pytest.approx(75.0)

    def test_already_correct_rate_is_idempotent(self, temp_db_engine):
        Base.metadata.create_all(bind=temp_db_engine)
        _seed_package(temp_db_engine, credits=100, price_usd=50.0, package_type="package")

        _run_init_db_against(temp_db_engine)
        _run_init_db_against(temp_db_engine)  # second boot should be a no-op

        with temp_db_engine.connect() as conn:
            row = conn.execute(
                text("SELECT price_usd FROM credit_packages WHERE package_type = 'package'")
            ).first()
        assert row.price_usd == pytest.approx(50.0)
