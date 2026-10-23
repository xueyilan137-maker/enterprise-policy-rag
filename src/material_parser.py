"""Strict CSV expense extraction. Uploaded cells are data, never instructions or code."""
import csv
import hashlib
import io
import re
from datetime import date

from pydantic import ValidationError
from src.rules_api import ExpenseItem

PARSER_VERSION = 'expense-csv-1.0.0'
MAX_BYTES = 256 * 1024
REQUIRED = {'item_id','category','amount','expense_date','receipt_id','receipt_present'}
FIELDS = set(ExpenseItem.model_fields)
BOOL_FIELDS = {'receipt_present','meal_provided','prior_approval_present'}
DATE_FIELDS = {'expense_date','check_in','check_out'}


def parse_expense_csv(raw):
    errors, items, locations = [], [], []
    def error(code, line=None, field=None):
        if len(errors) < 30:
            errors.append(dict(code=code, line=line, field=field))

    def result():
        return dict(parser_version=PARSER_VERSION,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw),
                    status='invalid' if errors else 'parsed',items=[] if errors else items,
                    row_locations=[] if errors else locations,errors=errors)

    if len(raw) > MAX_BYTES:
        error('TOO_LARGE');return result()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        error('INVALID_UTF8');return result()
    if not text.strip():
        error('EMPTY_FILE');return result()
    if any(ord(c) < 32 and c not in '\r\n\t' for c in text):
        error('CONTROL_CHARACTER');return result()
    reader = csv.reader(io.StringIO(text,newline=''),strict=True)
    try:
        header = next(reader)
        if len(header) != len(set(header)):
            error('DUPLICATE_COLUMN',1)
        for field in sorted(REQUIRED-set(header)):
            error('MISSING_COLUMN',1,field)
        for field in sorted(set(header)-FIELDS):
            error('UNKNOWN_COLUMN',1)  # Do not reflect arbitrary header contents.
        if errors:return result()
        seen = set()
        count = 0
        for row in reader:
            line = reader.line_num
            if not row:  # Truly empty lines only; delimiter-only rows are invalid items.
                continue
            count += 1
            if count > 200:
                error('ROW_LIMIT',line);break
            if len(row) != len(header):
                error('ROW_WIDTH',line);continue
            if any(len(value)>1000 for value in row):
                error('CELL_TOO_LONG',line);continue
            before = len(errors)
            data = {}
            for field,value in zip(header,row):
                value = value.strip()
                if value == '' and field not in ('item_id','category','amount'):
                    continue
                if field in BOOL_FIELDS:
                    if value not in ('true','false'):
                        error('INVALID_BOOLEAN',line,field);continue
                    data[field] = value == 'true'
                elif field == 'nights':
                    if not re.fullmatch(r'[1-9][0-9]{0,2}',value):
                        error('INVALID_NIGHTS',line,field);continue
                    data[field] = int(value)
                else:
                    data[field] = value
                if field in DATE_FIELDS:
                    try:
                        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError()
                        date.fromisoformat(value)
                    except ValueError:
                        error('INVALID_DATE',line,field)
            if data.get('category') not in ('meal','lodging','transit'):
                error('INVALID_CATEGORY',line,'category')
            try:
                item = ExpenseItem.model_validate(data).model_dump(exclude_none=True)
                if not item['item_id'] or item['item_id'] in seen:
                    error('DUPLICATE_OR_EMPTY_ITEM_ID',line,'item_id')
                seen.add(item['item_id'])
            except ValidationError as exc:
                for issue in exc.errors():
                    field = str(issue['loc'][0])
                    error('INVALID_AMOUNT' if field=='amount' else 'INVALID_ITEM_FIELD',line,field)
                continue
            if len(errors)==before:
                items.append(item)
                locations.append(dict(item_id=item['item_id'],ending_line=line))
        if count == 0:error('EMPTY_ITEMS')
    except (csv.Error,StopIteration):
        error('INVALID_CSV',reader.line_num)
    return result()
