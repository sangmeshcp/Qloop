"""
Generate Hypothesis strategies from a ParamSpace declaration.

Used by the property-test tier to fuzz parameterized circuits without
per-circuit strategy code.
"""

from __future__ import annotations

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from qloop.core.spec import BitstringDomain, ChoiceDomain, FloatDomain, IntDomain, ParamSpace


def strategies_for(space: ParamSpace) -> dict[str, SearchStrategy]:
    """
    Map each domain in space to a Hypothesis strategy.

    Returns a dict suitable for ``@given(**strategies_for(space))``.
    """
    result: dict[str, SearchStrategy] = {}
    for name, domain in space.domains.items():
        if isinstance(domain, BitstringDomain):
            result[name] = st.text(
                alphabet="01", min_size=domain.length, max_size=domain.length
            )
        elif isinstance(domain, FloatDomain):
            result[name] = st.floats(
                domain.min_val,
                domain.max_val,
                allow_nan=False,
                allow_infinity=False,
            )
        elif isinstance(domain, IntDomain):
            result[name] = st.integers(domain.min_val, domain.max_val)
        elif isinstance(domain, ChoiceDomain):
            result[name] = st.sampled_from(domain.options)
        else:
            raise ValueError(f"Unknown domain type for param '{name}': {type(domain)}")
    return result
