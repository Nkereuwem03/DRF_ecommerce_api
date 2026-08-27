import logging

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
)
from rest_framework.views import exception_handler

from config.error_handling.error_builders import build_error
from config.error_handling.error_codes import (
    INTERNAL_SERVER_ERROR,
    INVALID,
    INVALID_CREDENTIALS,
    PERMISSION_DENIED,
    RATE_LIMIT_EXCEEDED,
    REQUIRED,
    RESOURCE_NOT_FOUND,
)
from config.error_handling.error_types import (
    AUTHENTICATION_ERROR,
    AUTHORIZATION_ERROR,
    NOT_FOUND_ERROR,
    RATE_LIMIT_ERROR,
    SERVER_ERROR,
    VALIDATION_ERROR,
)
from config.error_handling.response import error_response

logger = logging.getLogger(__name__)

# Known DRF exceptions that deserve their own type/code,
# instead of being flattened into a generic validation error.
EXCEPTION_TYPE_MAP = {
    NotAuthenticated: (AUTHENTICATION_ERROR, INVALID_CREDENTIALS),
    AuthenticationFailed: (AUTHENTICATION_ERROR, INVALID_CREDENTIALS),
    PermissionDenied: (AUTHORIZATION_ERROR, PERMISSION_DENIED),
    NotFound: (NOT_FOUND_ERROR, RESOURCE_NOT_FOUND),
    Throttled: (RATE_LIMIT_ERROR, RATE_LIMIT_EXCEEDED),
}

REQUIRED_CODES = {"required", "null", "blank"}


def _resolve_code(detail) -> str:
    drf_code = getattr(detail, "code", None)
    if drf_code in REQUIRED_CODES:
        return REQUIRED
    return INVALID


def _flatten_errors(data, field_path=None) -> list:
    errors = []

    if isinstance(data, dict):
        for field, detail in data.items():
            path = f"{field_path}.{field}" if field_path else field
            errors.extend(_flatten_errors(detail, path))

    elif isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, (dict, list)):
                path = f"{field_path}[{index}]" if field_path else str(index)
                errors.extend(_flatten_errors(item, path))
            else:
                errors.append(
                    build_error(
                        error_type=VALIDATION_ERROR,
                        code=_resolve_code(item),
                        field=field_path,
                        message=str(item),
                    )
                )

    else:
        errors.append(
            build_error(
                error_type=VALIDATION_ERROR,
                code=_resolve_code(data),
                field=field_path,
                message=str(data),
            )
        )

    return errors


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Case 1: totally unknown exception, DRF couldn't classify it at all.
    if response is None:
        logger.exception("Unhandled exception")
        return error_response(
            message="Internal server error",
            errors=[
                build_error(
                    error_type=SERVER_ERROR,
                    code=INTERNAL_SERVER_ERROR,
                    message="An unexpected error occurred.",
                )
            ],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Case 2: known special case (not logged in, not allowed, not found, throttled).
    for exc_class, (error_type, error_code) in EXCEPTION_TYPE_MAP.items():
        if isinstance(exc, exc_class):
            message = (
                str(response.data.get("detail", exc.default_detail))
                if isinstance(response.data, dict)
                else str(exc)
            )
            return error_response(
                message=message,
                errors=[
                    build_error(
                        error_type=error_type,
                        code=error_code,
                        message=message,
                    )
                ],
                status_code=response.status_code,
            )

    # Case 3: everything else, normal serializer/field validation errors.
    errors = _flatten_errors(response.data)

    return error_response(
        message="Request failed",
        errors=errors,
        status_code=response.status_code,
    )
