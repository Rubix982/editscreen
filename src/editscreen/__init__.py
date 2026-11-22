"""Screen knowledge-editing evaluation items for contamination.

The question, in one sentence: **given a knowledge edit and an evaluation
probe, does the probe identify the edited subject?**

If it does, a score on that item cannot be evidence that the edit
propagated — the model can reach the answer by recalling what was just
written to it, without any propagation having occurred.

Nothing here loads a model, computes a gradient, or applies an edit. The
property being measured belongs to how the evaluation item was written,
not to how the weights were changed, so the answer is the same whether
the edit came from ROME, MEMIT, fine-tuning or a human.
"""

from .report import Report
from .screen import MATCHER_VERSION, screen, screen_items
from .types import Edit, Evidence, Item, Level, Verdict

__version__ = "0.1.0.dev0"

__all__ = [
    "Edit", "Item", "Level", "Verdict", "Evidence", "Report",
    "screen", "screen_items", "MATCHER_VERSION", "__version__",
]
