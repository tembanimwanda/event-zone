"""
tickets.py — PDF ticket generation for EventZone bookings.
Uses only the Python standard library (no reportlab/weasyprint dependency).
Generates a simple but clean PDF using raw PDF syntax.
"""

import io
from datetime import datetime


def generate_ticket_buffer(booking_id, user_email, user_name):
    """
    Generate a PDF ticket as a BytesIO buffer.
    Returns a BytesIO object ready to be sent as a file download.
    """
    booking_ref = f"EZ-{booking_id:06d}"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build a minimal valid PDF manually
    lines = []

    def add(s):
        lines.append(s)

    # PDF header
    add("%PDF-1.4")

    # Object 1 — Catalog
    obj1_offset = sum(len(l) + 1 for l in lines)
    add("1 0 obj")
    add("<< /Type /Catalog /Pages 2 0 R >>")
    add("endobj")

    # Object 2 — Pages
    obj2_offset = sum(len(l) + 1 for l in lines)
    add("2 0 obj")
    add("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add("endobj")

    # Object 3 — Page
    obj3_offset = sum(len(l) + 1 for l in lines)
    add("3 0 obj")
    add("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]")
    add("   /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>")
    add("endobj")

    # Build page content stream
    content_lines = [
        "BT",
        # Title
        "/F2 28 Tf",
        "50 780 Td",
        "(EventZone) Tj",
        # Subtitle
        "/F1 14 Tf",
        "0 -35 Td",
        "(E-Ticket Confirmation) Tj",
        # Divider line (drawn as text underline approximation)
        "/F1 10 Tf",
        "0 -10 Td",
        "(------------------------------------------------) Tj",
        # Booking ref
        "/F2 16 Tf",
        "0 -25 Td",
        f"(Booking Reference: {booking_ref}) Tj",
        # Guest info
        "/F1 12 Tf",
        "0 -30 Td",
        f"(Guest: {_safe(user_name)}) Tj",
        "0 -18 Td",
        f"(Email: {_safe(user_email)}) Tj",
        # Generated at
        "0 -30 Td",
        "(------------------------------------------------) Tj",
        "/F1 10 Tf",
        "0 -15 Td",
        f"(Generated: {generated_at}) Tj",
        "0 -15 Td",
        "(Please present this ticket at the venue entrance.) Tj",
        "ET",
    ]
    content_stream = "\n".join(content_lines)
    content_bytes = content_stream.encode("latin-1")

    # Object 4 — Content stream
    obj4_offset = sum(len(l) + 1 for l in lines)
    add("4 0 obj")
    add(f"<< /Length {len(content_bytes)} >>")
    add("stream")
    # We'll handle the binary stream separately
    stream_marker = len(lines)
    add("__STREAM_PLACEHOLDER__")
    add("endstream")
    add("endobj")

    # Object 5 — Font (Helvetica)
    obj5_offset = sum(len(l) + 1 for l in lines)
    add("5 0 obj")
    add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    add("endobj")

    # Object 6 — Font Bold (Helvetica-Bold)
    obj6_offset = sum(len(l) + 1 for l in lines)
    add("6 0 obj")
    add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    add("endobj")

    # Cross-reference table
    xref_offset = sum(len(l) + 1 for l in lines)

    # Build the final PDF bytes
    buf = io.BytesIO()

    # Write objects up to stream placeholder
    current_offset = 0
    offsets = {}
    obj_num = 0

    # Rebuild properly with correct offsets
    buf2 = io.BytesIO()

    def w(s):
        data = (s + "\n").encode("latin-1")
        buf2.write(data)
        return len(data)

    pos = 0
    pos += w("%PDF-1.4")

    offsets[1] = pos
    pos += w("1 0 obj")
    pos += w("<< /Type /Catalog /Pages 2 0 R >>")
    pos += w("endobj")

    offsets[2] = pos
    pos += w("2 0 obj")
    pos += w("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    pos += w("endobj")

    offsets[3] = pos
    pos += w("3 0 obj")
    pos += w("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]")
    pos += w("   /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>")
    pos += w("endobj")

    offsets[4] = pos
    pos += w("4 0 obj")
    pos += w(f"<< /Length {len(content_bytes)} >>")
    pos += w("stream")
    buf2.write(content_bytes)
    pos += len(content_bytes)
    pos += w("")
    pos += w("endstream")
    pos += w("endobj")

    offsets[5] = pos
    pos += w("5 0 obj")
    pos += w("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pos += w("endobj")

    offsets[6] = pos
    pos += w("6 0 obj")
    pos += w("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    pos += w("endobj")

    xref_pos = pos
    buf2.write(b"xref\n")
    buf2.write(f"0 7\n".encode())
    buf2.write(b"0000000000 65535 f \n")
    for i in range(1, 7):
        buf2.write(f"{offsets[i]:010d} 00000 n \n".encode())

    buf2.write(b"trailer\n")
    buf2.write(b"<< /Size 7 /Root 1 0 R >>\n")
    buf2.write(b"startxref\n")
    buf2.write(f"{xref_pos}\n".encode())
    buf2.write(b"%%EOF\n")

    buf2.seek(0)
    return buf2


def _safe(text):
    """Escape parentheses for PDF string literals."""
    if not text:
        return ""
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
