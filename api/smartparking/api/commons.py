from datetime import datetime, date, timedelta, timezone
from dataclasses import field, InitVar
from typing import Any, Optional, cast
from fastapi import APIRouter, Depends, Header, Query, Path, Request, Response, File, UploadFile
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass
from smartparking.model.errors import Errors
import smartparking.model.db as m
import smartparking.model.composite as c
from smartparking.service.base import ServiceContext
from smartparking.resources import context as r
from smartparking.api.shared.auth import with_user, with_token, maybe_user, Authorized
from smartparking.api.shared.errors import abort, abort_with, errorModel, ErrorResponse
from smartparking.api.shared.dependencies import URLFor
from smartparking.api.view import responses as vr
from smartparking.api.view import requests as vq