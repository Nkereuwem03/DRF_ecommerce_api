def build_error(
    *,
    error_type: str,
    code: str,
    message: str,
    field: str | None = None,
):
    error = {
        "type": error_type,
        "code": code,
        "message": message,
    }

    if field is not None:
        error["field"] = field

    return error