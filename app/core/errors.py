class ApplicationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


class DocumentError(ApplicationError):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(code, message, status_code)


class JobNotFound(ApplicationError):
    def __init__(self) -> None:
        super().__init__("JOB_NOT_FOUND", "ไม่พบงานนี้ หรือข้อมูลหมดอายุแล้ว", 404)


class QueueFull(ApplicationError):
    def __init__(self) -> None:
        super().__init__("JOB_QUEUE_FULL", "ระบบกำลังประมวลผลงานเต็ม โปรดลองอีกครั้งภายหลัง", 503, True)


class JobStorageLimitReached(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "JOB_STORAGE_LIMIT_REACHED",
            "มีงานที่ยังเก็บอยู่ครบจำนวนแล้ว โปรดลบงานเก่าก่อนเริ่มงานใหม่",
            409,
        )
