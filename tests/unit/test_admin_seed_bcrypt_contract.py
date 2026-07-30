"""S-01.4f / D-CP-4 — control-plane admin-seed bcrypt hash verifies in the instance.

At claim, the control plane seeds a new admin by inserting a ``users`` row with a
bcrypt password hash it computes itself (it holds the instance DB creds). This
pins the cross-repo contract: however the control plane produces that hash, the
instance's ``verify_password`` (raw ``bcrypt.checkpw``) MUST accept it — otherwise
a freshly-claimed customer can't log in.

Instance auth uses the ``bcrypt`` library directly (not passlib). Both raw
``bcrypt`` and passlib's bcrypt emit the standard ``$2b$`` format, so either is a
valid way for the control plane to compute the seed hash.
"""

import bcrypt
from passlib.hash import bcrypt as passlib_bcrypt

from backend.utils.auth import get_password_hash, verify_password

_PW = "alpha-bravo-charlie-42"


def test_instance_roundtrip():
    h = get_password_hash(_PW)
    assert verify_password(_PW, h) is True
    assert verify_password("not-the-value", h) is False


def test_control_plane_raw_bcrypt_hash_verifies():
    # The control plane can produce the hash exactly as the instance does —
    # standard bcrypt via bcrypt.hashpw — and it must verify via the instance path.
    cp_hash = bcrypt.hashpw(_PW.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    assert verify_password(_PW, cp_hash) is True
    assert cp_hash.startswith("$2")  # standard bcrypt format


def test_passlib_bcrypt_hash_also_verifies():
    # If the control plane used passlib's bcrypt instead, it emits the same
    # standard $2b$ format — must still verify (cross-library compatibility).
    cp_hash = passlib_bcrypt.hash(_PW)
    assert verify_password(_PW, cp_hash) is True
