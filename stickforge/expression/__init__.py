"""Facial expressions as blendable parameter sets composed into emotions."""

from .expression import (
    EXPRESSIONS,
    NEUTRAL,
    get_expression,
    blend_expression,
    register_expression,
)

__all__ = [
    "EXPRESSIONS",
    "NEUTRAL",
    "get_expression",
    "blend_expression",
    "register_expression",
]
