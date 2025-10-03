from __future__ import annotations

import json
from typing import Callable, Generator

from urllib.parse import urlencode

import os
import sys
import typing

import anyio
import pytest
from pydantic import typing as pydantic_typing
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_orig_forwardref_eval = typing.ForwardRef._evaluate  # type: ignore[attr-defined]


def _patched_forwardref_eval(self, globalns, localns, *args, **kwargs):  # type: ignore[no-untyped-def]
    if "recursive_guard" not in kwargs:
        kwargs["recursive_guard"] = set()
    return _orig_forwardref_eval(self, globalns, localns, *args, **kwargs)


typing.ForwardRef._evaluate = _patched_forwardref_eval  # type: ignore[attr-defined]

from app.db.session import get_db
from app.main import app
from app.models import AdminRoleEnum, AdminUser, Base
from app.utils.security import get_password_hash


_orig_evaluate_forwardref = pydantic_typing.evaluate_forwardref


def _patched_evaluate_forwardref(type_, globalns, localns):  # type: ignore[no-untyped-def]
    try:
        return _orig_evaluate_forwardref(type_, globalns, localns)
    except TypeError as exc:  # pragma: no cover - compatibility shim
        if "recursive_guard" in str(exc):
            return type_._evaluate(globalns, localns, None, recursive_guard=set())  # type: ignore[attr-defined]
        raise


pydantic_typing.evaluate_forwardref = _patched_evaluate_forwardref


class SimpleResponse:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def json(self) -> dict:
        if not self._body:
            return {}
        return json.loads(self._body.decode("utf-8"))


class SimpleTestClient:
    def __init__(self, app: Callable) -> None:
        self.app = app

    def request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> SimpleResponse:
        body = b""
        hdrs = headers.copy() if headers else {}
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            hdrs.setdefault("content-type", "application/json")

        raw_headers = [(name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in hdrs.items()]
        raw_headers.append((b"host", b"testserver"))

        query_string = b""
        if params:
            query_string = urlencode(params, doseq=True).encode("utf-8")

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "method": method.upper(),
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query_string,
            "headers": raw_headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        messages: list[dict] = []

        async def receive() -> dict:
            nonlocal body
            data = body
            body = b""
            return {"type": "http.request", "body": data, "more_body": False}

        async def send(message: dict) -> None:
            messages.append(message)

        async def run() -> None:
            await self.app(scope, receive, send)

        anyio.run(run)

        status_code = 500
        response_headers: dict[str, str] = {}
        response_body = b""
        for message in messages:
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                response_headers = {
                    k.decode("latin-1"): v.decode("latin-1") for k, v in message.get("headers", [])
                }
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")

        return SimpleResponse(status_code, response_headers, response_body)

    def get(
        self, path: str, headers: dict[str, str] | None = None, params: dict[str, str] | None = None
    ) -> SimpleResponse:
        return self.request("GET", path, headers=headers, params=params)

    def post(
        self,
        path: str,
        json: dict | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> SimpleResponse:
        return self.request("POST", path, json_data=json, headers=headers, params=params)


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[SimpleTestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield SimpleTestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session: Session) -> AdminUser:
    existing = db_session.query(AdminUser).filter(AdminUser.email == "admin@example.com").first()
    if existing:
        return existing
    user = AdminUser(
        email="admin@example.com",
        hashed_password=get_password_hash("Secretpass1!"),
        role=AdminRoleEnum.SUPERADMIN.value,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
