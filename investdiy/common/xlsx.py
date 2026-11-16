"""Read cached XLSX cell values without evaluating formulas or shifting empty cells."""

from io import BytesIO
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def worksheets(content):
    """Yield sparse rows keyed by Excel column letters, preserving empty cells."""
    with ZipFile(BytesIO(content)) as archive:
        shared = ([''.join(n.itertext()) for n in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
                  if 'xl/sharedStrings.xml' in archive.namelist() else [])
        for name in archive.namelist():
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name):
                continue
            rows = []
            for row in ET.fromstring(archive.read(name)).findall('.//s:row', NS):
                values = {}
                for cell in row.findall('s:c', NS):
                    value = cell.find('s:v', NS)
                    if value is not None:
                        value = shared[int(value.text)] if cell.get('t') == 's' else value.text
                    elif cell.get('t') == 'inlineStr':
                        value = ''.join(cell.find('s:is', NS).itertext())
                    else:
                        continue
                    values[re.sub(r'\d', '', cell.get('r'))] = value.strip()
                if values:
                    rows.append(values)
            yield rows
