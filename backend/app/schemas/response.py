from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class ApiResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }

    @staticmethod
    def ok(payload: Dict[str, Any]) -> "ApiResponse":
        return ApiResponse(success=True, data=payload, error=None)

    @staticmethod
    def fail(message: str) -> "ApiResponse":
        return ApiResponse(success=False, data=None, error=message)


@dataclass
class UploadResponseSchema:
    session_id: int
    status: str
    filename: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
