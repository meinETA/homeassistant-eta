"""Plant files are encrypted for the maintainers."""

import base64
import gzip
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import pytest

from custom_components.eta_webservices.seal import MAGIC, PUBLIC_KEY, seal


def _unseal(text: str, private: rsa.RSAPrivateKey) -> bytes:
    blob = base64.b64decode(text)
    assert blob[:4] == MAGIC
    size = int.from_bytes(blob[4:6], "big")
    wrapped = blob[6 : 6 + size]
    nonce = blob[6 + size : 18 + size]
    key = private.decrypt(
        wrapped,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return gzip.decompress(AESGCM(key).decrypt(nonce, blob[18 + size :], MAGIC))


@pytest.fixture(name="key")
def fixture_key(tmp_path: Path) -> tuple[rsa.RSAPrivateKey, Path]:
    """Throwaway key pair, public key as PEM file."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    path = tmp_path / "plant_key.pem"
    path.write_bytes(
        private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private, path


def test_seal_round_trip(key) -> None:
    """Only the private key gets the data back."""
    private, path = key
    data = b'{"tree": [{"uri": "120/10101/0/11060/0", "value": 31}]}'
    sealed = seal(data, path)
    assert b"10101" not in base64.b64decode(sealed)
    assert _unseal(sealed, private) == data


def test_seal_is_different_every_time(key) -> None:
    """Random key and nonce per file."""
    _, path = key
    assert seal(b"same", path) != seal(b"same", path)


def test_shipped_public_key_is_rsa_3072() -> None:
    """The integration ships the maintainers' public key."""
    key = serialization.load_pem_public_key(PUBLIC_KEY.read_bytes())
    assert isinstance(key, rsa.RSAPublicKey)
    assert key.key_size >= 3072
