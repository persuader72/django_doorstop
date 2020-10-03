from typing import Optional

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from doorstop.core.document import Document


def import_from_xslx(doc):
    #  type: (Document) -> None
    fields = ['uid', 'header', 'text', 'level', 'parent', 'subsystem']
    field_indexes = [-1, -1, -1, -1, -1, -1]

    def get_column_field(field, _ws, row):
        #  type: (str, Worksheet, int) -> Optional[str]
        _i = fields.index(field)
        _ii = field_indexes[_i]
        c = _ws.cell(row, _ii)
        if c is None or c.value is None:
            return None
        stripped = c.value.strip()
        if len(stripped) == 0:
            return None
        return stripped

    xlsxfile = '/tmp/import.xlsx'
    wb = load_workbook(xlsxfile)
    ws = wb.active

    keys = []
    cols = ws.max_column
    rows = ws.max_row
    for i in range(1, cols+1):
        keys.append(ws.cell(1, i).value.strip())
    for i in range(0, len(fields)):
        field_indexes[i] = keys.index(fields[i])+1

    for i in range(2, rows+1):
        uid = get_column_field('uid', ws, i)
        if uid is None:
            item = doc.add_item()
        else:
            item = doc.find_item(uid)

        item.header = get_column_field('header',ws, i)
        item.text = get_column_field('text',ws, i)
        level = get_column_field('level', ws, i)
        if level is not None:
            item.level = level
        parent = get_column_field('parent', ws, i)
        if parent is not None:
            pdoc = doc.tree.find_document('RADN')  # type: Document
            for pitem in pdoc.items:
                if pitem.get('orig_ref') == parent:
                    print(item.uid)
                    doc.tree.link_items(item.uid, pitem.uid)
        item.set('subsystem', get_column_field('subsystem',ws, i))


def export_to_xlsx(doc):
    # type: (Document) -> str
    xlsxfile = '/tmp/export.xlsx'
    wb = Workbook()
    ws = wb.active

    ws.cell(1, 1, "uid")
    ws.cell(1, 2, "header")
    ws.cell(1, 3, "text")
    ws.cell(1, 4, "level")
    ws.cell(1, 5, "parent")

    for i, ff in enumerate(doc.forgein_fields):
        ws.cell(1, 6+i, ff)

    print(doc.forgein_fields)

    last_row = 2
    for item in doc.items:
        ws.cell(last_row, 1, str(item.uid))
        ws.cell(last_row, 2, item.header)
        ws.cell(last_row, 3, item.text)
        ws.cell(last_row, 4, str(item.level))
        pitems = [x.uid.value for x in item.parent_items]
        ws.cell(last_row, 5, str(','.join(pitems)))

        for i, ff in enumerate(doc.forgein_fields):
            ffi = doc.forgein_fields[ff]
            if ffi['type'] == 'multi':
                ws.cell(last_row, 6+i, ','.join(item.get(ff)))
            else:
                ws.cell(last_row, 6+i, item.get(ff))
        last_row += 1
    wb.save(xlsxfile)
    return xlsxfile
