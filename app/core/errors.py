from __future__ import annotations

from typing import TypedDict


class ApiErrorDetail(TypedDict, total=False):
    message: str
    type: str
    code: str
    param: str


class ApiErrorEnvelope(TypedDict):
    error: ApiErrorDetail


class DashboardErrorDetail(TypedDict):
    code: str
    message: str


class DashboardErrorEnvelope(TypedDict):
    error: DashboardErrorDetail


def api_error(code: str, message: str, error_type: str = "server_error") -> ApiErrorEnvelope:
    return {"error": {"message": message, "type": error_type, "code": code}}


def dashboard_error(code: str, message: str) -> DashboardErrorEnvelope:
    return {"error": {"code": code, "message": message}}
