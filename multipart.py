"""
Minimal multipart/form-data parser for the single-file CV upload
endpoint. Avoids the deprecated/removed `cgi` module so this runs the
same on every Python 3.8+ interpreter, including the ones current
Coolify/Docker base images ship.
"""
import re

_BOUNDARY_RE = re.compile(r'boundary="?([^";]+)"?')
_DISPOSITION_RE = re.compile(
    r'Content-Disposition:\s*form-data;\s*name="([^"]*)"(?:;\s*filename="([^"]*)")?',
    re.IGNORECASE,
)


class MultipartError(ValueError):
    pass


def parse_first_file(content_type: str, body: bytes, field_name: str = "cv"):
    """
    Returns (filename, file_bytes) for the first file found under
    `field_name` in a multipart/form-data body. Raises MultipartError
    if the body isn't well-formed or the field is missing.
    """
    boundary_match = _BOUNDARY_RE.search(content_type or "")
    if not boundary_match:
        raise MultipartError("Missing multipart boundary")
    boundary = boundary_match.group(1).encode("utf-8")
    delimiter = b"--" + boundary

    parts = body.split(delimiter)
    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, _, content = part.partition(b"\r\n\r\n")
        if not content:
            continue
        try:
            header_text = header_blob.decode("utf-8", errors="ignore")
        except Exception:
            continue
        disp = _DISPOSITION_RE.search(header_text)
        if not disp:
            continue
        name, filename = disp.group(1), disp.group(2)
        if name != field_name or not filename:
            continue
        # Strip the trailing CRLF that precedes the next boundary.
        if content.endswith(b"\r\n"):
            content = content[:-2]
        return filename, content

    raise MultipartError(f"No file field named '{field_name}' found")
