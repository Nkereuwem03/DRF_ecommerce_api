from rest_framework import status
from rest_framework.response import Response


def api_response(
    *,
    success: bool,
    message: str,
    data=None,
    errors=None,
    status_code=status.HTTP_200_OK,
):
    payload = {
        "success": success,
        "message": message,
    }

    if success:
        payload["data"] = data if data is not None else {}
    else:
        payload["errors"] = errors if errors is not None else []

    return Response(payload, status=status_code)


def success_response(
    message="Success",
    data=None,
    status_code=status.HTTP_200_OK,
):
    return api_response(
        success=True,
        message=message,
        data=data,
        status_code=status_code,
    )


def error_response(
    message="Request failed",
    errors=None,
    status_code=status.HTTP_400_BAD_REQUEST,
):
    return api_response(
        success=False,
        message=message,
        errors=errors,
        status_code=status_code,
    )
