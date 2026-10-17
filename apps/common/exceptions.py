"""Tek hata formatı: {"error": {"code", "message", "details"}} (Bölüm 6)."""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class ApiError(APIException):
    """Servis ve view katmanının fırlattığı, hata koduna sahip istisna."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "validation_error"
    message = "İstek geçersiz."

    def __init__(self, message=None, *, code=None, status_code=None, details=None):
        self.code = code or self.code
        self.message = message or self.message
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(detail=self.message, code=self.code)


class ValidationFailed(ApiError):
    def __init__(self, message="İstek geçersiz.", *, details=None):
        super().__init__(message, details=details)


class InvalidSessionToken(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "invalid_session_token"
    message = "Oturum anahtarı geçersiz."


class NotFound(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Kayıt bulunamadı."


class QuestionMismatch(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "question_mismatch"
    message = "Gönderilen soru aktif soru değil."


class AlreadyAnswered(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_answered"
    message = "Bu soru zaten cevaplandı."


class SessionCompleted(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "session_completed"
    message = "Bu quiz oturumu tamamlandı."


class SessionAbandoned(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "session_abandoned"
    message = "Bu quiz oturumu uzun süre işlem görmediği için sona erdi."


class SessionNotCompleted(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "session_not_completed"
    message = "Quiz henüz tamamlanmadı."


class ScoreAlreadySaved(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "score_already_saved"
    message = "Bu oturum için skor zaten kaydedildi."


class ScoreRejected(ApiError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "score_rejected"
    message = "Cevap süren gerçekçi görünmediği için skor tabloya eklenemedi."


class CategoryUnavailable(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "category_unavailable"
    message = "Bu kategoride şu an yeterli soru yok."


_STATUS_CODES = {
    status.HTTP_400_BAD_REQUEST: ("validation_error", "İstek geçersiz."),
    status.HTTP_401_UNAUTHORIZED: ("invalid_session_token", "Oturum anahtarı geçersiz."),
    status.HTTP_403_FORBIDDEN: ("forbidden", "Bu işlem için yetkin yok."),
    status.HTTP_404_NOT_FOUND: ("not_found", "Kayıt bulunamadı."),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("method_not_allowed", "Bu metot desteklenmiyor."),
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: (
        "unsupported_media_type",
        "İstek gövdesi JSON olmalı.",
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: (
        "rate_limited",
        "Çok fazla istek gönderdin, biraz bekleyip tekrar dene.",
    ),
}


def error_body(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details or {}}}


def api_exception_handler(exc, context):
    if isinstance(exc, ApiError):
        return Response(error_body(exc.code, exc.message, exc.details), status=exc.status_code)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # 500: Django'nun handler500'ü (JSON) devralır

    code, message = _STATUS_CODES.get(response.status_code, ("error", "İşlem başarısız."))
    details = {}
    if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(
        response.data, dict | list
    ):
        details = (
            response.data
            if isinstance(response.data, dict)
            else {"non_field_errors": response.data}
        )
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS and getattr(exc, "wait", None):
        details = {"retry_after_seconds": int(exc.wait) + 1}
    response.data = error_body(code, message, details)
    return response
