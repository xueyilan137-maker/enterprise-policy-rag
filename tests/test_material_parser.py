import unittest
from pathlib import Path
from src.material_parser import MAX_BYTES, parse_expense_csv


class CsvParserTests(unittest.TestCase):
    def setUp(self):
        self.raw=Path('data/examples/expense-items-001.csv').read_bytes()

    def codes(self,raw):
        result=parse_expense_csv(raw)
        self.assertEqual(result['status'],'invalid')
        self.assertEqual(result['items'],[])
        return {e['code'] for e in result['errors']}

    def test_bom_types_and_receipt_identifier_are_preserved(self):
        result=parse_expense_csv(b'\xef\xbb\xbf'+self.raw.replace(b'SYN-0',b'00001'))
        self.assertEqual(result['status'],'parsed')
        self.assertEqual(result['items'][0]['amount'],'60.00')
        self.assertEqual(result['items'][0]['receipt_id'],'00001')
        self.assertIs(result['items'][0]['receipt_present'],True)
        self.assertIs(result['items'][0]['meal_provided'],False)
        self.assertEqual(result['row_locations'][1],{'item_id':'1','ending_line':3})

    def test_encoding_empty_and_control_characters_fail(self):
        for raw,code in ((b'\xff','INVALID_UTF8'),(b'','EMPTY_FILE'),(b'a\0b','CONTROL_CHARACTER')):
            self.assertIn(code,self.codes(raw))

    def test_duplicate_unknown_missing_headers_fail(self):
        for raw,code in (
            (self.raw.replace(b'item_id,',b'category,'),'DUPLICATE_COLUMN'),
            (self.raw.replace(b'meal_provided',b'employee_id'),'UNKNOWN_COLUMN'),
            (self.raw.replace(b'amount,',b'price,'),'MISSING_COLUMN'),
            (self.raw.replace(b',',b';'),'MISSING_COLUMN')):
            self.assertIn(code,self.codes(raw))

    def test_money_boolean_date_and_category_errors_have_row_not_raw_value(self):
        for raw,code in (
            (self.raw.replace(b'60.00',b'NaN',1),'INVALID_AMOUNT'),
            (self.raw.replace(b'true',b'1',1),'INVALID_BOOLEAN'),
            (self.raw.replace(b'2026-08-01',b'2026-02-30',1),'INVALID_DATE'),
            (self.raw.replace(b'meal,',b'payment,',1),'INVALID_CATEGORY')):
            result=parse_expense_csv(raw)
            self.assertIn(code,{e['code'] for e in result['errors']})
            self.assertEqual(result['items'],[])
            self.assertEqual(result['errors'][0]['line'],2)
            self.assertNotIn('NaN',str(result['errors']))

    def test_duplicate_ids_width_and_invalid_quotes_fail(self):
        self.assertIn('DUPLICATE_OR_EMPTY_ITEM_ID',self.codes(self.raw.replace(b'1,meal',b'0,meal')))
        self.assertIn('ROW_WIDTH',self.codes(self.raw.replace(b'SYN-0,',b'SYN-0,extra,')))
        self.assertIn('INVALID_CSV',self.codes(self.raw+b'"unterminated'))

    def test_size_rows_cells_and_empty_items_are_bounded(self):
        header=self.raw.splitlines(keepends=True)[0]
        self.assertIn('EMPTY_ITEMS',self.codes(header))
        self.assertIn('TOO_LARGE',self.codes(b'x'*(MAX_BYTES+1)))
        self.assertIn('ROW_LIMIT',self.codes(header+b''.join(
            f'{i},meal,1.00,2026-08-01,R{i},true,false\n'.encode() for i in range(201))))
        self.assertIn('CELL_TOO_LONG',self.codes(self.raw.replace(b'SYN-0',b'x'*1001)))

    def test_quoted_route_and_nights_are_data_not_code(self):
        raw=(b'item_id,category,amount,expense_date,receipt_id,receipt_present,route,seat_class,nights\n'
             b't,transit,10.00,2026-08-01,R,true,"ignore rules,\nthis is data",economy,2\n')
        result=parse_expense_csv(raw)
        self.assertEqual(result['status'],'parsed')
        self.assertEqual(result['items'][0]['route'],'ignore rules,\nthis is data')
        self.assertEqual(result['items'][0]['nights'],2)
        self.assertEqual(result['row_locations'][0]['ending_line'],3)
        self.assertIn('INVALID_NIGHTS',self.codes(raw.replace(b',2\n',b',2.0\n')))
