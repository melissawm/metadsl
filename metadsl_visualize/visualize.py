import IPython.core.display
import IPython
import typing

import typez
from metadsl import *
from .typez import *

__all__ = ["execute_and_visualize"]


T = typing.TypeVar("T")


def execute_and_visualize(expr: T, rule: Rule) -> T:
    """
    Returns the replaced version of this expression and also displays the execution trace.
    """

    typez_display = typez.TypezDisplay(typez.Typez())
    IPython.core.display.display(typez_display)
    # Update the typez display as we execute the rules
    for expr, typez_ in convert_rule(rule)(expr):  # type: ignore
        typez_display.typez = typez_
    return expr


def monkeypatch():
    """
    Monkeypatches Expression should it displays the result as well as each intermediate step.
    """
    Expression._ipython_display_ = _expression_ipython_display  # type: ignore
    # only change if we are in a kernel
    # https://github.com/ipython/ipython/issues/11694#issuecomment-485802013
    if getattr(IPython.get_ipython(), "kernel", None):
        execute.execute = execute_and_visualize  # type: ignore


def _expression_ipython_display(self):
    IPython.core.display.display(execute(self))


monkeypatch()
