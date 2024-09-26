import smartparking.service.account as as_
from smartparking.api.commons import (
    APIRouter,
    Authorized,
    Depends,
    Query,
    vr,
    with_token,
    with_user,
)

router = APIRouter()


@router.post(
    "",
    status_code=201,
    responses={
        201: {"description": "User information after successful signup."},
    },
)
async def signup(
    auth: Authorized = Depends(with_token),
) -> vr.Me:
    """
    Perform user signup.

    Args:
        auth (Authorized): Authorized user information obtained from the token.

    Returns:
        vr.Me: User information including account details and points.
    """
    login_id = auth.claims.get("sub", "")
    name = auth.claims.get("name", "")
    email = auth.claims.get("email", "")

    account, point = (await as_.signup(login_id, name, email)).get()
    return vr.Me.of(account)


@router.get(
    "",
    responses={
        200: {"description": "User information."},
    },
)
async def login(
    auth: Authorized = Depends(with_user),
) -> vr.Me:
    """
    Perform user login.

    Args:
        auth (Authorized): Authorized user information obtained from the user dependency.

    Returns:
        vr.Me: User information including account details and points.
    """
    login_id = auth.claims.get("sub", "")
    account, point = (await as_.login(login_id)).get()

    return vr.Me.of(account)


@router.delete(
    "",
    status_code=204,
    responses={
        204: {"description": "Successfully processed."},
    },
)
async def withdraw(
    auth: Authorized = Depends(with_user),
):
    """
    Withdraw from the service.

    Deletes all existing data and files along with the account information.

    Args:
        auth (Authorized): Authorized user information obtained from the user dependency.
    """
    await as_.withdraw(auth.me)


