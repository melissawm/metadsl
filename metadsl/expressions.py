from __future__ import annotations

import dataclasses
import typing
import typing_inspect
import itertools

from .typing_tools import *

__all__ = [
    "Expression",
    "expression",
    "ExpressionFolder",
    "ExpressionReplacer",
    "LiteralExpression",
    "E",
]

T_expression = typing.TypeVar("T_expression", bound="Expression")


@dataclasses.dataclass(eq=False, repr=False)
class Expression(GenericCheck):
    """
    Subclass this type and provide relevent methods for your type. Do not add any fields.

    If the `function` is called with `arguments` then it should return `self`.

    The arguments should match the proper types specified in the type annotation of the function.
    The return type of the function should either be the the expression itself or
    LiteralExpression of the return type.
    """

    function: typing.Callable
    args: typing.Tuple[object, ...]
    kwargs: typing.Mapping[str, object]

    def __str__(self):
        arg_strings = (str(arg) for arg in self.args)
        kwarg_strings = (f"{str(k)}={str(v)}" for k, v in self.kwargs.items())
        return f"{self._function_str}({', '.join(itertools.chain(arg_strings, kwarg_strings))})"

    @property
    def _function_str(self):
        return self.function.__qualname__

    @property
    def _type_str(self):
        t = get_type(self)
        return getattr(t, "__qualname__", str(t))

    def __repr__(self):
        return f"{self._type_str}({self._function_str}, {repr(self.args)}, {repr(self.kwargs)})"

    def __eq__(self, value) -> bool:
        """
        Only equal if generic types and values are equal.
        """
        if not isinstance(value, Expression):
            return False

        return (
            self.function == value.function
            and get_type(self) == get_type(value)
            and self.args == value.args
            and self.kwargs == value.kwargs
        )


T = typing.TypeVar("T")


class LiteralExpression(Expression, typing.Generic[T]):
    """
    This is meant to be used when are computing a Python value that is not an expression.
    """

    ...


E = typing.Union[T, LiteralExpression[T]]


def extract_expression_type(t: typing.Type) -> typing.Type[Expression]:
    """
    If t is an expression type, return it, otherwise, it should be a union of an expression type and  non expression type
    """
    if typing_inspect.is_union_type(t):
        expression_args = [
            arg for arg in typing_inspect.get_args(t) if issubclass(arg, Expression)
        ]
        if len(expression_args) != 1:
            raise TypeError(
                f"Union must contain exactly one expression type, not {len(expression_args)}: {t}"
            )
        return expression_args[0]
    if issubclass(t, Expression):
        return t
    raise TypeError(f"{t} is not an expression type")


def wrap_infer(
    fn: typing.Callable[..., T],
    args: typing.Tuple[object, ...],
    kwargs: typing.Mapping[str, object],
    return_type: typing.Type[T],
) -> T:
    """
    Given a function and some arguments, return the right expression for the return type.
    """

    expr_return_type = extract_expression_type(return_type)

    return typing.cast(T, expr_return_type(fn, args, kwargs))


T_callable = typing.TypeVar("T_callable", bound=typing.Callable)


def expression(fn: T_callable) -> T_callable:
    """
    Creates an expresion object by wrapping a Python function and providing a function
    that will take in the args and return an expression of the right type.
    """

    return typing.cast(T_callable, infer(fn, wrap_infer))


T_Expression = typing.TypeVar("T_Expression", bound="Expression")


@dataclasses.dataclass
class ExpressionFolder:
    """
    Traverses this expression graph and transforms each node, from the bottom up.
    """

    fn: typing.Callable[[object], object]

    def __call__(self, expr: object):
        fn: typing.Callable[[object], object] = self.fn  # type: ignore
        if isinstance(expr, Expression):
            t: typing.Type[Expression] = get_type(expr)
            return fn(
                t(
                    expr.function,
                    tuple(self(arg) for arg in expr.args),
                    {k: self(v) for k, v in expr.kwargs},
                )
            )
        return fn(expr)


@dataclasses.dataclass
class ExpressionReplacer:
    """
    Replaces certain subexpression in an expression with values.
    """

    mapping: typing.Mapping
    folder: ExpressionFolder = dataclasses.field(init=False)

    def __post_init__(self):
        self.folder = ExpressionFolder(self.fn)

    def __call__(self, expr):
        return self.folder(expr)

    def fn(self, o):
        return self.mapping.get(o, o)
