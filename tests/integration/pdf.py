"""Write minimal text-only PDFs that Tika can read."""


def write_pdf(path, pages: list[list[str]]) -> None:
    """Write one PDF page per entry in ``pages``, one text line per string."""
    font = 3 + 2 * len(pages)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (b" ".join(b"%d 0 R" % (3 + 2 * i) for i in range(len(pages))), len(pages)),
    ]
    for i, lines in enumerate(pages):
        text = b"".join(b"(%s) Tj T*\n" % _escape(line) for line in lines)
        stream = b"BT /F1 12 Tf 72 720 Td 16 TL\n" + text + b"ET"
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>" % (font, 4 + 2 * i)
        )
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


def _escape(line: str) -> bytes:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")
