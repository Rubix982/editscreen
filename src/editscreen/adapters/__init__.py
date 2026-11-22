"""One module per source format.

Each adapter's only job is to turn a file into `Item`s. No adapter
screens anything, so a wrong adapter produces a loud failure rather than
a plausible-looking rate.
"""

from . import generic

__all__ = ["generic"]
