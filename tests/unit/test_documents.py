from io import BytesIO
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import DocumentError
from app.documents.reader import DocumentReader
from PIL import Image
from pypdf import PdfWriter


def make_pdf(page_count: int = 1, *, password: str | None = None) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    if password:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def make_png(size: tuple[int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, "white").save(output, format="PNG")
    return output.getvalue()


def test_pdf_is_staged_and_pages_are_counted(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path))

    document = reader.prepare(BytesIO(make_pdf(2)), "หลายหน้า.pdf", uuid4())

    assert document.media_type == "application/pdf"
    assert document.page_count == 2
    assert document.source_path.is_file()


def test_password_protected_pdf_has_specific_error(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path))

    try:
        reader.prepare(BytesIO(make_pdf(password="secret")), "locked.pdf", uuid4())
    except DocumentError as error:
        assert error.code == "PDF_PASSWORD_PROTECTED"
        assert error.status_code == 422
    else:
        raise AssertionError("Expected protected PDF to be rejected")


def test_pdf_page_limit_is_checked_before_queuing(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path, max_pages=1))

    try:
        reader.prepare(BytesIO(make_pdf(2)), "too-many.pdf", uuid4())
    except DocumentError as error:
        assert error.code == "PAGE_LIMIT_EXCEEDED"
    else:
        raise AssertionError("Expected page count to be rejected")


def test_file_signature_is_used_instead_of_client_filename(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path))

    try:
        reader.prepare(BytesIO(b"not a pdf or supported image"), "scan.png", uuid4())
    except DocumentError as error:
        assert error.code == "UNSUPPORTED_FILE_TYPE"
        assert error.status_code == 415
    else:
        raise AssertionError("Expected unsupported data to be rejected")


def test_oversized_upload_is_rejected_and_removed(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path, max_upload_bytes=1024))
    job_id = uuid4()

    try:
        reader.prepare(BytesIO(b"A" * 1025), "large.png", job_id)
    except DocumentError as error:
        assert error.code == "FILE_TOO_LARGE"
        assert error.status_code == 413
    else:
        raise AssertionError("Expected file size to be rejected")
    assert list(tmp_path.iterdir()) == []


def test_page_pixel_limit_is_checked_before_decoding(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path, max_page_pixels=1_000_000))

    try:
        reader.prepare(BytesIO(make_png((1001, 1000))), "large.png", uuid4())
    except DocumentError as error:
        assert error.code == "PAGE_PIXEL_LIMIT_EXCEEDED"
    else:
        raise AssertionError("Expected page pixel count to be rejected")


def test_page_dimension_limit_is_enforced(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path, max_dimension=1000))

    try:
        reader.prepare(BytesIO(make_png((1001, 10))), "wide.png", uuid4())
    except DocumentError as error:
        assert error.code == "PAGE_DIMENSION_LIMIT_EXCEEDED"
    else:
        raise AssertionError("Expected page dimension to be rejected")


def test_pdf_total_pixel_budget_is_enforced(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path, max_total_pixels=3_000_000))

    try:
        reader.prepare(BytesIO(make_pdf(2)), "many-pixels.pdf", uuid4())
    except DocumentError as error:
        assert error.code == "PDF_PIXEL_LIMIT_EXCEEDED"
    else:
        raise AssertionError("Expected total PDF pixel budget to be rejected")


def test_source_name_is_reduced_to_a_display_basename(tmp_path) -> None:
    reader = DocumentReader(Settings(storage_dir=tmp_path))

    document = reader.prepare(BytesIO(make_png((2, 2))), r"C:\private\scan.png", uuid4())

    assert document.source_name == "scan.png"
