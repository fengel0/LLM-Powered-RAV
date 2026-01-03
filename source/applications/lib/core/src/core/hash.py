from hashlib import sha256


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    return prefix + sha256(content.encode()).hexdigest()
