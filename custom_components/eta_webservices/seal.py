"""Encrypt plant files before they leave Home Assistant.

Plant files are attached to public GitHub issues. Only the maintainers can read
them: the content is compressed and encrypted with a random AES-256-GCM key,
that key is encrypted with the RSA public key below (OAEP, SHA-256). The
private key is kept outside this repository.

Format (base64): b"ETA1" | key length (2 bytes) | RSA-encrypted key | nonce (12) | AES-GCM ciphertext
"""

from __future__ import annotations

import base64
import gzip
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"ETA1"
PUBLIC_KEY = Path(__file__).parent / "plant_key.pem"


def _public_key(path: Path = PUBLIC_KEY) -> rsa.RSAPublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError("plant key is not an RSA key")
    return key


def seal(data: bytes, path: Path = PUBLIC_KEY) -> str:
    """Compress and encrypt data for the maintainers, return base64."""
    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    body = AESGCM(key).encrypt(nonce, gzip.compress(data), MAGIC)
    wrapped = _public_key(path).encrypt(
        key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    blob = MAGIC + len(wrapped).to_bytes(2, "big") + wrapped + nonce + body
    return base64.b64encode(blob).decode("ascii")
