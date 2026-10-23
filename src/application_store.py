"""SQLite repository for immutable applications and one durable precheck per application."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


class Conflict(ValueError):
    pass


class ApplicationStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] not in (0,1,2,3,4):
                raise RuntimeError('Unsupported database schema; preserve data')
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS applications (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                    payload_hash TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(owner, idempotency_key));
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, application_id TEXT NOT NULL UNIQUE REFERENCES applications(id),
                    status TEXT NOT NULL CHECK(status IN ('pending','running','completed','failed','indeterminate')),
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    result TEXT, error_code TEXT, workflow_run_id TEXT);
                CREATE TABLE IF NOT EXISTS job_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES jobs(id),
                    status TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS materials (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, source_name TEXT NOT NULL,
                    sha256 TEXT NOT NULL, parser_version TEXT NOT NULL, raw BLOB NOT NULL,
                    parsing TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(owner,sha256,parser_version));
                CREATE TABLE IF NOT EXISTS application_materials (
                    application_id TEXT NOT NULL REFERENCES applications(id),
                    material_id TEXT NOT NULL REFERENCES materials(id),
                    PRIMARY KEY(application_id,material_id));
                CREATE TABLE IF NOT EXISTS extractions (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    narrative_id TEXT NOT NULL REFERENCES materials(id), csv_id TEXT NOT NULL REFERENCES materials(id),
                    extractor_version TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                    result TEXT,error_code TEXT,workflow_run_id TEXT,
                    UNIQUE(owner,narrative_id,csv_id,extractor_version));
                CREATE TABLE IF NOT EXISTS application_extractions (
                    application_id TEXT PRIMARY KEY REFERENCES applications(id),extraction_id TEXT NOT NULL REFERENCES extractions(id));
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
                    reviewer TEXT NOT NULL,decision TEXT NOT NULL,note TEXT NOT NULL,
                    report_sha256 TEXT NOT NULL,created_at TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,payload_hash TEXT NOT NULL,
                    UNIQUE(reviewer,idempotency_key));
                PRAGMA user_version=4;
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, owner, key, payload, material_id=None, narrative_id=None, extraction_id=None):
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        hashed = encoded if material_id is None else encoded+'\0'+material_id
        if extraction_id is not None:hashed+='\0'+narrative_id+'\0'+extraction_id
        digest = hashlib.sha256(hashed.encode('utf-8')).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if extraction_id is not None:
                record=db.execute('SELECT * FROM extractions WHERE id=? AND owner=?',(extraction_id,owner)).fetchone()
                if (not record or record['status']!='completed' or record['narrative_id']!=narrative_id or record['csv_id']!=material_id or
                        json.loads(record['result'])['validation']['status']!='validated'):
                    raise ValueError('Unvalidated extraction')
            if material_id is not None:
                source = db.execute('SELECT parsing FROM materials WHERE id=? AND owner=?',(material_id,owner)).fetchone()
                if source is None or json.loads(source['parsing'])['status']!='parsed':
                    raise ValueError('Invalid owned material')
            old = db.execute('SELECT * FROM applications WHERE owner=? AND idempotency_key=?', (owner,key)).fetchone()
            if old:
                if old['payload_hash'] != digest:
                    raise Conflict('Idempotency key reused for different application')
                return old['id'], False
            id = str(uuid4())
            db.execute('INSERT INTO applications VALUES (?,?,?,?,?,?)', (id,owner,key,digest,encoded,now()))
            if material_id is not None:
                db.execute('INSERT INTO application_materials VALUES (?,?)',(id,material_id))
            if extraction_id is not None:
                db.execute('INSERT INTO application_materials VALUES (?,?)',(id,narrative_id))
                db.execute('INSERT INTO application_extractions VALUES (?,?)',(id,extraction_id))
            return id, True

    def enqueue_extraction(self,owner,narrative_id,csv_id,version):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT id FROM extractions WHERE owner=? AND narrative_id=? AND csv_id=? AND extractor_version=?',
                           (owner,narrative_id,csv_id,version)).fetchone()
            if old:return old['id'],False
            for id in (narrative_id,csv_id):
                if not db.execute('SELECT 1 FROM materials WHERE id=? AND owner=?',(id,owner)).fetchone():raise ValueError('Invalid source')
            id,stamp=str(uuid4()),now()
            db.execute('INSERT INTO extractions(id,owner,narrative_id,csv_id,extractor_version,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                       (id,owner,narrative_id,csv_id,version,'pending',stamp,stamp))
            return id,True

    def extraction(self,id,owner):
        with self.connect() as db:
            row=db.execute('SELECT * FROM extractions WHERE id=? AND owner=?',(id,owner)).fetchone()
            if not row:return None
            result={k:row[k] for k in row.keys() if k not in ('owner','result')}
            result['extraction_id']=result.pop('id')
            result['result']=json.loads(row['result']) if row['result'] else None
            return result

    def claim_extraction(self,id):
        with self.connect() as db:
            changed=db.execute("UPDATE extractions SET status='running',updated_at=? WHERE id=? AND status='pending'",(now(),id)).rowcount
            if not changed:return None
            row=db.execute('SELECT * FROM extractions WHERE id=?',(id,)).fetchone()
            materials=[json.loads(db.execute('SELECT parsing FROM materials WHERE id=?',(row[k],)).fetchone()['parsing'])
                       for k in ('narrative_id','csv_id')]
            return materials

    def finish_extraction(self,id,status,result=None,error=None,run_id=None):
        with self.connect() as db:
            db.execute("UPDATE extractions SET status=?,updated_at=?,result=?,error_code=?,workflow_run_id=? WHERE id=? AND status='running'",
                (status,now(),json.dumps(result,ensure_ascii=False) if result else None,error,run_id,id))

    def save_material(self, owner, source_name, raw, parsing):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT id FROM materials WHERE owner=? AND sha256=? AND parser_version=?',
                (owner,parsing['sha256'],parsing['parser_version'])).fetchone()
            if old:return old['id'],False
            id = str(uuid4())
            db.execute('INSERT INTO materials VALUES (?,?,?,?,?,?,?,?)',
                (id,owner,source_name,parsing['sha256'],parsing['parser_version'],raw,json.dumps(parsing,ensure_ascii=False),now()))
            return id,True

    def material(self, id, owner):
        with self.connect() as db:
            row = db.execute('SELECT id,source_name,parsing,created_at FROM materials WHERE id=? AND owner=?',(id,owner)).fetchone()
            return dict(material_id=row['id'],source_name=row['source_name'],created_at=row['created_at'],
                        **json.loads(row['parsing'])) if row else None

    def application(self, id, owner):
        with self.connect() as db:
            row = db.execute('SELECT id,payload,created_at FROM applications WHERE id=? AND owner=?', (id,owner)).fetchone()
            if not row:
                return None
            job = db.execute('SELECT * FROM jobs WHERE application_id=?', (id,)).fetchone()
            sources = [dict(r) for r in db.execute('SELECT m.id AS material_id,m.sha256,m.parser_version FROM materials m '
                'JOIN application_materials l ON l.material_id=m.id WHERE l.application_id=?',(id,))]
            extraction=db.execute('SELECT extraction_id FROM application_extractions WHERE application_id=?',(id,)).fetchone()
            return dict(application_id=row['id'], created_at=row['created_at'],extraction_id=extraction['extraction_id'] if extraction else None,
                        application=json.loads(row['payload']), materials=sources,precheck=self.job_dict(db,job) if job else None,
                        review=self.review_dict(db,job['id']) if job else None)

    @staticmethod
    def review_dict(db,job_id):
        row=db.execute('SELECT id,job_id,reviewer,decision,note,report_sha256,created_at FROM reviews WHERE job_id=?',(job_id,)).fetchone()
        return dict(row) if row else None

    def applications(self,owner=None,limit=30,offset=0):
        with self.connect() as db:
            where='WHERE a.owner=?' if owner is not None else ''
            args=(owner,) if owner is not None else ()
            rows=db.execute('SELECT a.id,a.owner,a.payload,a.created_at,j.id AS job_id,j.status,j.result,r.decision '
                'FROM applications a LEFT JOIN jobs j ON j.application_id=a.id LEFT JOIN reviews r ON r.job_id=j.id '
                +where+' ORDER BY a.created_at DESC,a.id DESC LIMIT ? OFFSET ?',args+(limit,offset)).fetchall()
            total=db.execute('SELECT COUNT(*) FROM applications a '+where,args).fetchone()[0]
            items=[]
            for row in rows:
                data=json.loads(row['payload']);result=json.loads(row['result']) if row['result'] else None
                items.append(dict(application_id=row['id'],employee_id=row['owner'],created_at=row['created_at'],
                    destination=data.get('destination'),reason=data.get('reason'),total_amount=data.get('total_amount'),
                    trip_start_date=data.get('trip_start_date'),job_id=row['job_id'],job_status=row['status'],
                    precheck_status=result['report']['status'] if result else None,review_decision=row['decision']))
            return dict(items=items,total=total,limit=limit,offset=offset)

    def extractions(self,owner):
        with self.connect() as db:
            rows=db.execute('SELECT id FROM extractions WHERE owner=? ORDER BY created_at DESC,id DESC LIMIT 20',(owner,)).fetchall()
        return [self.extraction(row['id'],owner) for row in rows]

    def review_bundle(self,id):
        # This cross-owner method is only exposed behind the finance role dependency.
        with self.connect() as db:
            row=db.execute('SELECT owner FROM applications WHERE id=?',(id,)).fetchone()
        if not row:return None
        app=self.application(id,row['owner'])
        app['source_materials']=[self.material(m['material_id'],row['owner']) for m in app['materials']]
        app['extraction']=self.extraction(app['extraction_id'],row['owner']) if app['extraction_id'] else None
        return app

    def save_review(self,application_id,reviewer,key,decision,note):
        payload=json.dumps(dict(application_id=application_id,decision=decision,note=note),sort_keys=True,ensure_ascii=False)
        digest=hashlib.sha256(payload.encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM reviews WHERE reviewer=? AND idempotency_key=?',(reviewer,key)).fetchone()
            if old:
                if old['payload_hash']!=digest:raise Conflict('Review idempotency conflict')
                return self.review_dict(db,old['job_id']),False
            job=db.execute('SELECT j.*,a.owner FROM jobs j JOIN applications a ON a.id=j.application_id WHERE a.id=?',(application_id,)).fetchone()
            if not job or job['status']!='completed' or not job['result']:
                raise ValueError('Completed precheck required')
            if job['owner']==reviewer:raise ValueError('Self review is forbidden')
            if self.review_dict(db,job['id']):raise Conflict('Report already reviewed')
            report_hash=hashlib.sha256(job['result'].encode('utf-8')).hexdigest()
            db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?)',
                (str(uuid4()),job['id'],reviewer,decision,note,report_hash,now(),key,digest))
            return self.review_dict(db,job['id']),True

    def enqueue(self, id, owner):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM applications WHERE id=? AND owner=?', (id,owner)).fetchone():
                return None, False
            old = db.execute('SELECT id FROM jobs WHERE application_id=?', (id,)).fetchone()
            if old:
                return old['id'], False
            job_id, stamp = str(uuid4()), now()
            db.execute('INSERT INTO jobs(id,application_id,status,created_at,updated_at) VALUES (?,?,?,?,?)',
                       (job_id,id,'pending',stamp,stamp))
            db.execute('INSERT INTO job_events(job_id,status,created_at) VALUES (?,?,?)', (job_id,'pending',stamp))
            return job_id, True

    @staticmethod
    def job_dict(db, row):
        result = {k: row[k] for k in ('id','application_id','status','created_at','updated_at','error_code','workflow_run_id')}
        result['job_id'] = result.pop('id')
        result['result'] = json.loads(row['result']) if row['result'] else None
        result['events'] = [dict(event) for event in db.execute(
            'SELECT status,created_at FROM job_events WHERE job_id=? ORDER BY seq', (row['id'],))]
        return result

    def job(self, job_id, owner):
        with self.connect() as db:
            row = db.execute('SELECT j.* FROM jobs j JOIN applications a ON a.id=j.application_id WHERE j.id=? AND a.owner=?',
                             (job_id,owner)).fetchone()
            return self.job_dict(db,row) if row else None

    def claim(self, job_id):
        with self.connect() as db:
            stamp = now()
            changed = db.execute("UPDATE jobs SET status='running',updated_at=? WHERE id=? AND status='pending'", (stamp,job_id)).rowcount
            if not changed:
                return None
            db.execute('INSERT INTO job_events(job_id,status,created_at) VALUES (?,?,?)', (job_id,'running',stamp))
            row = db.execute('SELECT a.payload FROM applications a JOIN jobs j ON j.application_id=a.id WHERE j.id=?', (job_id,)).fetchone()
            return json.loads(row['payload'])

    def finish(self, job_id, status, result=None, error=None, run_id=None):
        if status not in ('completed','failed','indeterminate'):
            raise ValueError('Invalid terminal state')
        with self.connect() as db:
            stamp = now()
            changed = db.execute('UPDATE jobs SET status=?,updated_at=?,result=?,error_code=?,workflow_run_id=? WHERE id=? AND status=\'running\'',
                (status,stamp,json.dumps(result,ensure_ascii=False) if result else None,error,run_id,job_id)).rowcount
            if changed:
                db.execute('INSERT INTO job_events(job_id,status,created_at) VALUES (?,?,?)', (job_id,status,stamp))

    def recover(self):
        # Single API process only. Never re-execute jobs whose remote outcome is unknown.
        with self.connect() as db:
            stamp = now()
            rows = db.execute("SELECT id,status FROM jobs WHERE status IN ('pending','running')").fetchall()
            for row in rows:
                status = 'indeterminate' if row['status']=='running' else 'failed'
                db.execute('UPDATE jobs SET status=?,error_code=?,updated_at=? WHERE id=?',
                           (status,'service_interrupted',stamp,row['id']))
                db.execute('INSERT INTO job_events(job_id,status,created_at) VALUES (?,?,?)', (row['id'],status,stamp))
            db.execute("UPDATE extractions SET status=CASE status WHEN 'running' THEN 'indeterminate' ELSE 'failed' END,"
                       "error_code='service_interrupted',updated_at=? WHERE status IN ('pending','running')",(stamp,))
