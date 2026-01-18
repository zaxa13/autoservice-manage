from fastapi import HTTPException, status


class AutoserviceException(HTTPException):
    """Базовое исключение приложения"""
    pass


class NotFoundException(AutoserviceException):
    """Ресурс не найден"""
    def __init__(self, detail: str = "Ресурс не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(AutoserviceException):
    """Некорректный запрос"""
    def __init__(self, detail: str = "Некорректный запрос"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(AutoserviceException):
    """Не авторизован"""
    def __init__(self, detail: str = "Требуется аутентификация"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(AutoserviceException):
    """Доступ запрещен"""
    def __init__(self, detail: str = "Недостаточно прав доступа"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

