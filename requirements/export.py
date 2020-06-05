from openpyxl import Workbook

from doorstop.core.document import Document


def export_to_xlsx(doc):
    # type: (Document) -> str
    xlsxfile = '/tmp/export.xlsx'
    wb = Workbook()
    ws = wb.active

    ws.cell(1, 1, "ID")
    ws.cell(1, 2, "Header")
    ws.cell(1, 3, "Text")
    ws.cell(1, 4, "Level")
    #ws.cell(1, 5, "SubSys")

    last_row = 2
    for item in doc.items:
        ws.cell(last_row, 1, str(item.uid))
        ws.cell(last_row, 2, item.header)
        ws.cell(last_row, 3, item.text)
        ws.cell(last_row, 4, str(item.level))
        #ws.cell(last_row, 5, item.get('subsys'))
        last_row += 1
    wb.save(xlsxfile)
    return xlsxfile