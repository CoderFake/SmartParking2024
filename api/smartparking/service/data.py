import json
from typing import Any, Dict
from uuid import uuid4

from smartparking.ext.image.base import ImageContent, load_image
from pydantic import RootModel
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import desc, func

from .commons import (
    Errorneous,
    Errors,
    Maybe,
    Optional,
    c,
    datetime,
    delete,
    insert,
    m,
    r,
    select,
    service,
    update,
)

