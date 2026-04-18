"""Kit utilities package."""


def generate_uuid() -> str:
    """Generate UUID."""
    import uuid
    return str(uuid.uuid4())