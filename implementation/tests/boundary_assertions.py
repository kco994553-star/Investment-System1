"""Shared regression assertion for retired public report/collector routes."""
from contextlib import contextmanager
from hashlib import sha256
import pytest
from investment_system.public_price_boundary import PublicPriceBoundaryError


@contextmanager
def route_withheld_without_writes(root):
    def inventory():
        return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*') if p.is_file()}
    before = inventory()
    with pytest.raises(PublicPriceBoundaryError, match='^PUBLIC_PRICE_BOUNDARY: route withheld under GSQ-010$'):
        yield
    assert inventory() == before
