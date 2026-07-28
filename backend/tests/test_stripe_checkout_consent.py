"""Server-side Terms/Refund consent enforcement at checkout (GAP review fix).

A client-only checkbox is bypassable; the checkout endpoint must reject a purchase
without consent and persist the accepted version to the audit trail.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.routers.stripe_checkout import create_checkout_session
from backend.schemas.stripe_schemas import CheckoutSessionRequest

# Call the undecorated handler so the slowapi rate-limit wrapper (which requires a
# real starlette Request + app state) doesn't interfere with unit testing the logic.
_endpoint = getattr(create_checkout_session, "__wrapped__", create_checkout_session)


def _body(accepted: bool) -> CheckoutSessionRequest:
    return CheckoutSessionRequest(
        package_id="pkg-1",
        success_url="https://app/success",
        cancel_url="https://app/cancel",
        accepted_terms=accepted,
        consent_version="2026-07-27",
    )


@pytest.mark.asyncio
async def test_checkout_rejected_without_consent():
    with pytest.raises(HTTPException) as ei:
        await _endpoint(MagicMock(), _body(False), MagicMock(), MagicMock(id="u1"))
    assert ei.value.status_code == 400
    assert "Terms" in str(ei.value.detail)


@pytest.mark.asyncio
async def test_checkout_records_consent_and_proceeds():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock()  # package exists
    user = MagicMock(id="u1", email="u@x.com")

    with patch("backend.services.audit_service.log_action") as log_action, patch(
        "backend.services.audit_service.get_client_ip", return_value="1.2.3.4"
    ), patch(
        "backend.routers.stripe_checkout.stripe_service.create_checkout_session",
        return_value={"checkout_url": "https://stripe/x", "session_id": "cs_1"},
    ):
        resp = await _endpoint(MagicMock(), _body(True), db, user)

    assert resp.checkout_url == "https://stripe/x"
    log_action.assert_called_once()
    kwargs = log_action.call_args.kwargs
    assert kwargs["resource_type"] == "payment"
    assert kwargs["metadata"]["accepted_terms"] is True
    assert kwargs["metadata"]["consent_version"] == "2026-07-27"
    assert kwargs["ip_address"] == "1.2.3.4"


@pytest.mark.asyncio
async def test_default_request_is_not_consented():
    # accepted_terms defaults False, so a request that omits it is rejected.
    body = CheckoutSessionRequest(
        package_id="pkg-1", success_url="https://app/s", cancel_url="https://app/c"
    )
    assert body.accepted_terms is False
