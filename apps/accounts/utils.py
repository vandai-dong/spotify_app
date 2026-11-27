import secrets
import string

_ALPHABET = string.ascii_letters + string.digits


def generate_random_username(length=26):
    """Return a random alphanumeric username (cryptographically random)."""
    return ''.join(secrets.choice(_ALPHABET) for _ in range(length))
