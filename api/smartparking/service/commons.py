from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass
from typing import Any, Optional
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.orm import aliased, contains_eager
from smartparking.resources import context as r
import smartparking.model.db as m
import smartparking.model.composite as c
from smartparking.model.errors import Errors, Errorneous
from .base import service, Maybe