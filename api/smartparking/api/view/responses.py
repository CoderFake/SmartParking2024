from datetime import datetime
from typing import Any, Optional

import smartparking.model.composite as c
from smartparking.api.shared.dependencies import URLFor
from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.dataclasses import dataclass
from typing_extensions import Self


# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------
def to_lower_camel(name: str) -> str:
    """
    Convert a snake_case string to lowerCamelCase.

    Args:
        name (str): The snake_case string.

    Returns:
        str: The converted lowerCamelCase string.
    """
    return "".join(
        [n.capitalize() if i > 0 else n for i, n in enumerate(name.split("_"))]
    )


config = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


@dataclass(config=config)
class Me:
    """
    Represents a user account with essential information.
    """
    id: str = Field(description="Account ID.")
    created_at: datetime = Field(description="Registration date and time.")
    modified_at: datetime = Field(description="Last modification date and time.")

    @classmethod
    def of(cls, me: c.Me) -> Self:

        return cls(id=me.id, created_at = me.created_at,modified_at=me.modified_at)
