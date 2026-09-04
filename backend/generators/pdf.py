from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from backend.generators.common import output_path


def create_pdf(filename: str, title: str, content: str) -> dict[str, object]:
    path = output_path(filename, '.pdf')
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setTitle(title)

    width, height = letter
    left = 0.8 * inch
    right = width - 0.8 * inch
    y = height - 0.8 * inch
    body_size = 11
    line_height = 16
    max_width = right - left

    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(left, y, title[:90])
    y -= 30

    def new_page() -> float:
        pdf.showPage()
        pdf.setFont('Helvetica', body_size)
        return height - 0.75 * inch

    def draw_wrapped(line: str, font='Helvetica', size=body_size) -> None:
        nonlocal y
        pdf.setFont(font, size)
        words = line.split()
        if not words:
            y -= line_height
            return
        current = ''
        for word in words:
            candidate = word if not current else current + ' ' + word
            if stringWidth(candidate, font, size) > max_width and current:
                if y < 0.75 * inch:
                    y = new_page()
                pdf.drawString(left, y, current)
                y -= line_height
                current = word
            else:
                current = candidate
        if y < 0.75 * inch:
            y = new_page()
        pdf.drawString(left, y, current)
        y -= line_height

    for raw_line in content.splitlines() or ['']:
        line = raw_line.strip()
        if not line:
            y -= line_height * 0.6
            continue
        if line.isupper() or line[:2].isdigit() or line.startswith(tuple(f'{i}.' for i in range(1, 10))):
            draw_wrapped(line, 'Helvetica-Bold', body_size)
        else:
            draw_wrapped(line)

    pdf.save()

    # Artifact validation
    if not path.exists():
        raise RuntimeError(f'PDF was not created at {path}')
    size = path.stat().st_size
    if size < 1000:
        raise RuntimeError(f'PDF is suspiciously small ({size} bytes) — content may be empty')

    return {'success': True, 'file': str(path), 'type': 'pdf'}