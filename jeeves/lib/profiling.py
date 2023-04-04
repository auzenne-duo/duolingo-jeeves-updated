import os
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

_T = TypeVar("_T")


def traced_function(
    *, name: Optional[str] = None, **kwargs: Any
) -> Callable[[Callable[..., _T]], Callable[..., _T]]:
    """
    Traces a function with OpenTelemetry.
    Parameters:
        name: The name to use in OpenTelemetry. If not provided, defaults to a
            sensible, descriptive default. The default is `ClassName.func_name`
            if the function is a class method, or `file_name::func_name`
            otherwise. We recommend using this default, unless for some reason
            that name would not be sufficiently descriptive (e.g., if the
            function is defined in `__init__.py` and is not a class method).
        attributes: A dictionary of attributes to add to the span.
    Returns:
        A decorator for tracing the function.
    """
    if os.environ.get("OTEL_TRACES_EXPORTER", "none") == "none":
        # Skip over decorator logic to make debugging easier.
        return lambda fn: fn

    def _get_descriptive_name(fn: Callable[..., _T]) -> str:
        qualified_name = fn.__qualname__
        # The qualname looks like `MyClass.my_function` -- but only if the
        # function was defined within a class! If that's the case, great. To
        # test if a function was defined in a class, we cheat by seeing if the
        # the qualified name has a `.` in it.
        if "." in qualified_name:
            return qualified_name
        # Otherwise, we we want to give a bit more context, so let's prepend
        # the file name instead.
        filename = fn.__code__.co_filename
        if not filename:
            # If for whatever reason we didn't find a filename, just return
            # what we have
            return qualified_name
        # This filename isn't perfect; if we're decorating a function that was
        # was already decorated, `co_filename` actually refers to the
        # filename of the previous decorator... but for us, it's usually good
        # enough.
        # We only want the filename, not the directory
        filename = filename.split("/")[-1]
        # Also remove the trailing `.py[c]``
        filename = filename.removesuffix(".py").removesuffix(".pyc")
        # Prepend the filename to the qualified name
        return f"{filename}::{qualified_name}"

    def decorator(fn: Callable[..., _T]) -> Callable[..., _T]:
        # If name isn't provided, we compute a good one ourselves
        try:
            descriptive_name = name if name is not None else _get_descriptive_name(fn)
        except Exception:  # pylint: disable=broad-except
            descriptive_name = "unknown"

        attributes: Dict[str, str] = {}
        attributes["function_qualified_name"] = fn.__qualname__

        return wraps(fn)(
            tracer.start_as_current_span(name=descriptive_name, attributes=attributes, **kwargs)(fn)
        )

    return decorator
