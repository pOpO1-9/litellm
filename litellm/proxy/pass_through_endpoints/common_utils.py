from collections.abc import Mapping, Sequence
from typing import Final, TypeVar

from fastapi import Request
from pydantic import TypeAdapter

from litellm.proxy._types import PassThroughGenericEndpoint

_PassThroughEntry: Final = TypeVar("_PassThroughEntry", bound=Mapping[str, object] | PassThroughGenericEndpoint)
_ENDPOINT_DICT: Final = TypeAdapter(dict[str, object])


def get_litellm_virtual_key(request: Request) -> str:
    """
    Extract and format API key from request headers.
    Prioritizes x-litellm-api-key over Authorization header.


    Vertex JS SDK uses `Authorization` header, we use `x-litellm-api-key` to pass litellm virtual key

    """
    litellm_api_key: Final = request.headers.get("x-litellm-api-key")
    if litellm_api_key:
        return f"Bearer {litellm_api_key}"
    return request.headers.get("Authorization", "")


def _pass_through_path(endpoint: Mapping[str, object] | PassThroughGenericEndpoint) -> object:
    return endpoint.path if isinstance(endpoint, PassThroughGenericEndpoint) else endpoint.get("path")


def merge_db_and_config_pass_through_endpoints(
    db_endpoints: Sequence[_PassThroughEntry],
    config_endpoints: Sequence[_PassThroughEntry],
) -> tuple[_PassThroughEntry, ...]:
    db_paths: Final = frozenset(_pass_through_path(endpoint) for endpoint in db_endpoints)
    return (
        *db_endpoints,
        *(endpoint for endpoint in config_endpoints if _pass_through_path(endpoint) not in db_paths),
    )


def served_pass_through_endpoints(
    db_endpoints: object,
    config_endpoints: Sequence[Mapping[str, object]] | None,
) -> tuple[Mapping[str, object], ...]:
    stored_entries: Final = db_endpoints if isinstance(db_endpoints, list) else ()
    stored: Final = tuple(_ENDPOINT_DICT.validate_python(entry) for entry in stored_entries if isinstance(entry, dict))
    return merge_db_and_config_pass_through_endpoints(stored, tuple(config_endpoints or ()))


def pass_through_caller_key_header(endpoint: Mapping[str, object]) -> str | None:
    headers: Final = endpoint.get("headers")
    header_name: Final = (
        _ENDPOINT_DICT.validate_python(headers).get("litellm_user_api_key") if isinstance(headers, dict) else None
    )
    return header_name if isinstance(header_name, str) else None
