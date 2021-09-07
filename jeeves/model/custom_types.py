"""
Custom types used for type hints

"""

from typing import Any, Dict, List, Union

JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
