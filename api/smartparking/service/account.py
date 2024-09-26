from typing import Any, Dict, cast
from uuid import uuid4

from smartparking.ext.firebase.base import FirebaseAdmin
from firebase_admin.auth import delete_user
from sqlalchemy import cast as Cast
from sqlalchemy import (
    delete,
    func,
    insert,
    literal_column,
    not_,
    or_,
    select,
    union_all,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import Date, String

from .commons import Errors, Maybe, c, datetime, m, r, service


@service
async def signup(login_id: str, name: str, email: str) -> Maybe[c.Me]:
    """
    Perform signup and register user information. Does not raise an error if the user is already signed up.

    Args:
        login_id (str): The login ID.
        name (str): The user's name.
        email (str): The user's email address.

    Returns:
        Maybe[c.Me]: The signed-up user information along with total points.
    """
    # Acquire a lock on the account row to prevent race conditions
    account = await r.tx.scalar(
        select(m.Account).where(m.Account.login_id == login_id).with_for_update()
    )

    now = datetime.now()

    if account is None:

        account = await r.tx.scalar(
            insert(m.Account).returning(m.Account),
            dict(
                id=str(uuid4()),
                login_id=login_id,
                name=name,
                email=email,
                created_at=now,
                modified_at=now,
                last_login=now,
            ),
        )

    return await r.tx.get(c.Me, account.id)


@service
async def login(login_id: str) -> Maybe[c.Me]:
    """
    Perform login.

    Args:
        login_id (str): The login ID.

    Returns:
        Maybe[c.Me]: The user information along with total points. Returns an error if unauthorized.
    """
    # Retrieve the account based on login_id
    account = await r.tx.scalar(select(m.Account).where(m.Account.login_id == login_id))
    now = datetime.now()

    if account is None:
        return Errors.UNAUTHORIZED

    # Update the last_login timestamp
    await r.tx.execute(
        update(m.Account).where(m.Account.login_id == login_id).values(last_login=now)
    )
    await r.tx.commit()

    return await r.tx.get(c.Me, account.id)


@service
async def withdraw(me: c.Me):
    """
    Delete user information and related data.

    Args:
        me (c.Me): The authenticated user.
    """
    # Retrieve the resume item to get the photo path for deletion
    resume = await r.tx.scalar(
        select(m.ResumeItem).where(m.ResumeItem.account_id == me.id)
    )

    path = resume and resume.photo

    # Delete the account from the database
    await r.tx.execute(delete(m.Account).where(m.Account.id == me.id))

    if path:
        try:
            # Attempt to delete the resume photo from storage
            r.storage.delete(path)
        except Exception as e:
            r.logger.warning(f"Failed to delete resume photo at {path}", exc_info=e)

    try:
        # Attempt to delete the Firebase user
        firebase = cast(FirebaseAdmin, r.firebase).app
        delete_user(me.login_id, app=firebase)
    except Exception as e:
        r.logger.warning(f"Failed to delete Firebase user {me.login_id}", exc_info=e)
