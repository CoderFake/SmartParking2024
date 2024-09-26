from typing import Any
from fastapi import Request, Header
from smartparking.ext.storage.local import LocalStorage


class URLFor:
    def __init__(
        self,
        request: Request,
        x_script_name: str | None = Header(default=None, include_in_schema=False),
        x_forwarded_proto: str | None = Header(default=None, include_in_schema=False),
    ) -> None:
        self.request = request
        self.script = x_script_name
        self.proto = x_forwarded_proto

    def __call__(self, path: str) -> str:
        scheme = self.proto or self.request.url.scheme
        netloc = self.request.url.netloc
        script = f"{self.script}/" if self.script else ""

        return f'{scheme}://{netloc}/{script}/{path}'

    def storage(self, path: str) -> str:
        from smartparking.resources import context as r
        from smartparking.config import environment

        static = environment().settings.static

        if static:
            static_path = static.path + '/'
        else:
            static_path = '/'

        return r.storage.urlize(path, root=self(static_path))