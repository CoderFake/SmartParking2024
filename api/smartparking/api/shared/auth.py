from dataclasses import dataclass
from typing import Any, Optional, Generic, TypeVar, Dict
from fastapi import Header, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from smartparking.model.errors import Errors, Errorneous
from smartparking.resources import context as r
import smartparking.model.composite as c
from .errors import abort, abort_with

Me = TypeVar('Me')


@dataclass
class Authorized(Generic[Me]):
    me: Me
    claims: Dict[str, Any]


class Authorization(Generic[Me]):
    """
    A dependency object type that performs Bearer authentication.
    """

    async def __call__(
            self,
            authorization: Optional[str] = Header(default=None),
    ) -> Authorized[Me]:
        """
        Perform Bearer authentication on the Authorization header and return an authorized object containing user information.

        Args:
            authorization (Optional[str]): The Authorization header.

        Returns:
            Authorized[Me]: The authorized object containing user information and claims.

        Raises:
            HTTPException: If authentication fails.
        """
        if not authorization:
            return Authorized(self.no_auth(), {})
        elif not authorization.startswith('Bearer '):
            abort(401, code=Errors.UNAUTHORIZED.name, message="Invalid authorization header")

        token = authorization[7:]
        try:
            claims = r.auth.verify(token)
        except Exception as e:
            abort(401, code=Errors.UNAUTHORIZED.name, message="Token verification failed")

        me = await self.authorize(claims)

        return Authorized(me, claims)

    def no_auth(self) -> Me:
        """
        Handle cases where no authentication is provided.

        Returns:
            Me: The result when no authentication is present.

        Raises:
            HTTPException: Always raises an unauthorized exception.
        """
        abort(401, code=Errors.UNAUTHORIZED.name, message="Bearer token is not set")

    async def authorize(self, claims: Dict[str, Any]) -> Me:
        """
        Authorize the user based on the provided claims.

        Args:
            claims (Dict[str, Any]): The claims extracted from the token.

        Returns:
            Me: The authorized user object.

        Raises:
            NotImplementedError: If not overridden in a subclass.
        """
        raise NotImplementedError()


class WithToken(Authorization[None]):
    """
    Authorization class that only requires a valid Bearer token without associating it with a user.
    """

    async def authorize(self, claims: Dict[str, Any]) -> None:
        """
        Authorize based on the token claims without retrieving user information.

        Args:
            claims (Dict[str, Any]): The claims extracted from the token.

        Returns:
            None
        """
        return None


class WithUser(Authorization[c.Me]):
    """
    Authorization class that requires a valid Bearer token and associates it with a user.
    """

    async def authorize(self, claims: Dict[str, Any]) -> c.Me:
        """
        Authorize the user by retrieving user information based on the token claims.

        Args:
            claims (Dict[str, Any]): The claims extracted from the token.

        Returns:
            c.Me: The authenticated user object.

        Raises:
            HTTPException: If the user is not signed up.
        """
        from smartparking.service.account import login

        result = await login(claims['sub'])
        if isinstance(result, Errorneous):
            abort_with(401, Errors.NOT_SIGNED_UP.name, "Not signed up yet")
        return result.value  # Assuming `Maybe` has a `value` attribute for successful results


class MaybeUser(Authorization[Optional[c.Me]]):
    """
    Authorization class that may or may not associate the Bearer token with a user.
    """

    def no_auth(self, *args) -> Optional[c.Me]:
        """
        Handle cases where no authentication is provided by returning None.

        Returns:
            Optional[c.Me]: None, indicating no user is authenticated.
        """
        return None

    async def authorize(self, claims: Dict[str, Any]) -> Optional[c.Me]:
        """
        Attempt to authorize the user, returning None if the user is not signed up.

        Args:
            claims (Dict[str, Any]): The claims extracted from the token.

        Returns:
            Optional[c.Me]: The authenticated user object or None.
        """
        from smartparking.service.account import login

        result = await login(claims['sub'])
        if isinstance(result, Errorneous):
            return self.no_auth()
        return result.value  # Assuming `Maybe` has a `value` attribute for successful results


# ----------------------------------------------------------------
# Dependencies
# ----------------------------------------------------------------
with_token = WithToken()
with_user = WithUser()
maybe_user = MaybeUser()
