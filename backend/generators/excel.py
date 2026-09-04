from openpyxl import Workbook
from backend.generators.common import output_path


def create_excel(filename: str, sheet_name: str, columns: list[str], rows: list[list[object]]) -> dict[str, object]:
    path = output_path(filename, '.xlsx')
    book = Workbook()
    sheet = book.active
    sheet.title = sheet_name[:31] or 'Sheet1'
    if columns:
        sheet.append(columns)
    for row in rows:
        sheet.append(row)
    book.save(path)

    # Artifact validation
    if not path.exists():
        raise RuntimeError(f'Excel workbook was not created at {path}')
    if sheet.max_row < 1:
        raise RuntimeError('Excel workbook has no rows — content was not written')
    if not rows:
        raise RuntimeError('Excel workbook has no data rows — content generation may have failed')

    return {'success': True, 'file': str(path), 'type': 'xlsx'}
