"""Local document text extraction and evidence validation for model candidates."""
import hashlib
import io
import json
import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, StrictStr, ValidationError
from src.rules_api import Money

FIELDS = ('trip_start_date','trip_end_date','submitted_date','destination','destination_region','reason','total_amount')
EXTRACTOR_VERSION = 'travel-extract-1.0.2'
TEXT_VERSION = 'narrative-text-1.0.1'
DATE_TOKEN = r'(?:\d{4}-\d{1,2}-\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)'
DATE_LABELS = {
    'trip_start_date': r'出差开始日期|出发日期|出发时间|行程开始|出发',
    'trip_end_date': r'出差结束日期|返程日期|返程时间|行程结束|返程',
    'submitted_date': r'申请提交日期|提交日期|提交时间',
}


class Claim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: StrictStr | None
    quote: StrictStr | None


class Candidate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fields: dict[str,Claim]
    conflicts: list[StrictStr]


class AmountCheck(BaseModel):
    value: Money


def normalize_date(value):
    parts = re.findall(r'\d+',value)
    if len(parts)!=3:raise ValueError('Full date required')
    return date(*map(int,parts)).isoformat()


def parse_narrative(raw, kind):
    result = dict(kind='narrative',format=kind,parser_version=TEXT_VERSION+'-'+kind,sha256=hashlib.sha256(raw).hexdigest(),
                  size_bytes=len(raw),status='invalid',text='',pages=[],errors=[])
    try:
        if kind=='md':
            if len(raw)>256*1024:raise ValueError('TOO_LARGE')
            text=raw.decode('utf-8-sig').strip()
            pages=[]
        elif kind=='pdf':
            from pypdf import PdfReader
            if len(raw)>2*1024*1024:raise ValueError('TOO_LARGE')
            if not raw.startswith(b'%PDF-'):raise ValueError('INVALID_PDF')
            reader=PdfReader(io.BytesIO(raw),strict=True)
            if reader.is_encrypted:raise ValueError('ENCRYPTED_PDF')
            if not 1<=len(reader.pages)<=10:raise ValueError('PAGE_LIMIT')
            text='';pages=[]
            for number,page in enumerate(reader.pages,1):
                part=(page.extract_text() or '').strip()
                if not part:raise ValueError('PAGE_WITHOUT_TEXT')
                if text:text+='\n\n'
                start=len(text);text+=part
                pages.append(dict(page=number,start=start,end=len(text)))
                if len(text)>20000:raise ValueError('TEXT_LIMIT')
        else:raise ValueError('UNSUPPORTED_FORMAT')
        if not text:raise ValueError('EMPTY_TEXT')
        if len(text)>20000:raise ValueError('TEXT_LIMIT')
        if '\ufffd' in text or any(ord(c)<32 and c not in '\t\n\r' for c in text):raise ValueError('UNREADABLE_TEXT')
        result.update(status='parsed',text=text,pages=pages)
    except UnicodeDecodeError:
        result['errors']=[dict(code='INVALID_UTF8')]
    except ValueError as exc:
        known={'TOO_LARGE','INVALID_PDF','ENCRYPTED_PDF','PAGE_LIMIT','PAGE_WITHOUT_TEXT','TEXT_LIMIT','EMPTY_TEXT','UNREADABLE_TEXT','UNSUPPORTED_FORMAT'}
        result['errors']=[dict(code=str(exc) if str(exc) in known else 'INVALID_DOCUMENT')]
    except Exception:
        result['errors']=[dict(code='INVALID_DOCUMENT')]
    return result


def validate_candidate(document, raw_model, items):
    text=document['text'];issues=[];values={};evidence={}
    def issue(code,field=None,severity='needs_manual_review'):
        issues.append(dict(code=code,field=field,severity=severity))
    try:
        if len(raw_model)>24000:raise ValueError()
        candidate=Candidate.model_validate(json.loads(raw_model))
        if set(candidate.fields)!=set(FIELDS) or any(x not in FIELDS for x in candidate.conflicts):raise ValueError()
    except (ValueError,TypeError,ValidationError):
        return dict(status='needs_manual_review',values={},evidence={},issues=[dict(code='INVALID_MODEL_SCHEMA',field=None,severity='needs_manual_review')])
    if re.search(r'忽略.{0,20}(制度|规则|CSV|指令)|直接.{0,6}(批准|核定|付款)|ignore.{0,20}(rules?|instructions?)',text,re.I):
        issue('INSTRUCTION_LIKE_TEXT')
    for field in candidate.conflicts:issue('MODEL_REPORTED_CONFLICT',field)
    for field,claim in candidate.fields.items():
        value,quote=claim.value,claim.quote
        if value is None:
            issue('MISSING_FIELD',field,'needs_materials');continue
        if not value or len(value)>500 or not quote or len(quote)>2000 or quote not in text:
            issue('UNSUPPORTED_EVIDENCE',field);continue
        if text.count(quote)!=1:
            issue('AMBIGUOUS_QUOTE',field);continue
        start=text.index(quote);end=start+len(quote)
        location=dict(quote=quote,char_start=start,char_end=end,start_line=text[:start].count('\n')+1,end_line=text[:end].count('\n')+1)
        location['pages']=[p['page'] for p in document.get('pages',[]) if p['start']<end and start<p['end']]
        evidence[field]=location
        try:
            if field in DATE_LABELS:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError()
                date.fromisoformat(value)
                tokens={normalize_date(x) for x in re.findall(DATE_TOKEN,quote)}
                if tokens!={value}:raise ValueError()
            elif field=='total_amount':
                AmountCheck(value=value)
                amounts={format(Decimal(m),'0.2f') for m in re.findall(r'(?<![\d.])(?:0|[1-9]\d*)(?:\.\d{1,2})?(?![\d.])',quote)}
                if value not in amounts:raise ValueError()
            elif field=='destination_region':
                if value!='CN-mainland' or not any(x in quote for x in ('中国大陆','境内','CN-mainland')):raise ValueError()
            elif value not in quote:raise ValueError()
        except (ValueError,ValidationError):
            issue('VALUE_NOT_SUPPORTED_BY_QUOTE',field);continue
        values[field]=value
    # Independent checks stop a model from choosing one of multiple explicit dates/totals.
    for field,labels in DATE_LABELS.items():
        found=re.findall(r'(?:'+labels+r')\s*(?:为|是|[:：])?\s*('+DATE_TOKEN+r')',text)
        if field=='trip_start_date':found+=re.findall('('+DATE_TOKEN+r')\s*(?:出发|启程)',text)
        if field=='trip_end_date':found+=re.findall('('+DATE_TOKEN+r')\s*(?:返程|返回)',text)
        try:dates={normalize_date(x) for x in found}
        except ValueError:dates=set();issue('INVALID_SOURCE_DATE',field)
        if len(dates)>1:issue('SOURCE_DATE_CONFLICT',field)
        elif field in values and dates!={values[field]}:issue('DATE_ROLE_UNVERIFIED',field)
    declared=re.findall(r'(?:申请总额|申报总额|报销总额|费用合计|总金额)\s*(?:为|是|[:：])?\s*(\d+(?:\.\d{1,2})?)(?![\d.])',text)
    totals={format(Decimal(x),'0.2f') for x in declared}
    if len(totals)>1:issue('SOURCE_TOTAL_CONFLICT','total_amount')
    elif 'total_amount' in values and totals!={values['total_amount']}:issue('TOTAL_ROLE_UNVERIFIED','total_amount')
    if all(k in values for k in ('trip_start_date','trip_end_date','submitted_date')):
        if values['trip_start_date']>values['trip_end_date'] or values['submitted_date']<values['trip_end_date']:
            issue('DATE_ORDER_CONFLICT')
        for item in items:
            for key in ('expense_date','check_in','check_out'):
                if key=='expense_date' and not item.get(key):issue('CSV_MISSING_DATE',key,'needs_materials')
                if item.get(key) and not values['trip_start_date']<=item[key]<=values['trip_end_date']:
                    issue('CSV_DATE_CONFLICT',key)
    if 'total_amount' in values:
        total=sum((Decimal(item['amount']) for item in items),Decimal('0.00'))
        if Decimal(values['total_amount'])!=total:issue('CSV_TOTAL_CONFLICT','total_amount')
    status='needs_manual_review' if any(i['severity']=='needs_manual_review' for i in issues) else 'needs_materials' if issues else 'validated'
    return dict(status=status,values=values,evidence=evidence,issues=issues)
