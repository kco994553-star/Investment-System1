"""Private ownership-scoped SQLite adapter for synthetic finance. No production vault claim."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from uuid import uuid4
from .domain import PlatformError, Principal, aware, json_text

class ScopedStore:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        existing=self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        version=self.db.execute("PRAGMA user_version").fetchone()[0]
        if existing and version!=1:
            self.db.close()
            raise PlatformError("SCHEMA_MIGRATION_REQUIRED")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY,user_id TEXT,tenant_id TEXT,provider TEXT,state TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,user_id TEXT,tenant_id TEXT,connection_id TEXT,resource TEXT,sha256 TEXT,body BLOB,fetched_at TEXT);
        CREATE TABLE IF NOT EXISTS records(seq INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,tenant_id TEXT,connection_id TEXT,resource TEXT,object_id TEXT,revision INTEGER,account_id TEXT,effective_at TEXT,available_at TEXT,receipt_id TEXT,payload TEXT,sha256 TEXT,
        UNIQUE(user_id,tenant_id,connection_id,resource,object_id,revision));
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,user_id TEXT,tenant_id TEXT,connection_id TEXT,state TEXT,started_at TEXT,completed_at TEXT,error_code TEXT);
        CREATE TABLE IF NOT EXISTS cursors(user_id TEXT,tenant_id TEXT,connection_id TEXT,resource TEXT,value TEXT,PRIMARY KEY(user_id,tenant_id,connection_id,resource));
        CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,user_id TEXT,tenant_id TEXT,connection_id TEXT,available_at TEXT,payload TEXT,sha256 TEXT);
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,tenant_id TEXT,event TEXT,object_id TEXT,at TEXT);
        ''')
        self.db.execute("PRAGMA user_version=1")
        self.db.commit()

    def close(self):
        with self.lock:
            self.db.close()

    @staticmethod
    def scope(p):
        if not isinstance(p, Principal) or not p.user_id or not p.tenant_id or not p.session_id:
            raise PlatformError("UNAUTHENTICATED")
        return (p.user_id, p.tenant_id)

    def connection(self, p, cid):
        with self.lock:
            row = self.db.execute("SELECT * FROM connections WHERE user_id=? AND tenant_id=? AND id=?", (*self.scope(p),cid)).fetchone()
            if row is None:
                raise PlatformError("NOT_FOUND")
            return dict(row)

    def connections(self, p):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM connections WHERE user_id=? AND tenant_id=?", self.scope(p))]

    def create_connection(self, p, provider, now):
        cid = uuid4().hex
        with self.lock, self.db:
            self.db.execute("INSERT INTO connections VALUES (?,?,?,?,?,?)", (cid,*self.scope(p),provider,"ACTIVE",aware(now).isoformat()))
            self.event(p,"CONNECTION_CREATED",cid,now)
        return cid

    def revoke(self, p, cid, now):
        self.connection(p,cid)
        with self.lock, self.db:
            self.db.execute("UPDATE connections SET state='REVOKED' WHERE user_id=? AND tenant_id=? AND id=?", (*self.scope(p),cid))
            self.event(p,"CONNECTION_REVOKED",cid,now)

    def event(self, p, event, object_id, now):
        # Internal event enum and opaque object ids only, never provider error/body/token.
        if event not in {"CONNECTION_CREATED","CONNECTION_REVOKED","SYNC_STARTED","SYNC_COMPLETED","SYNC_FAILED","DATA_EXPORTED","SECURITY_EVENT"}:
            raise PlatformError("INVALID_EVENT")
        self.db.execute("INSERT INTO audit(user_id,tenant_id,event,object_id,at) VALUES (?,?,?,?,?)", (*self.scope(p),event,object_id,aware(now).isoformat()))

    def audit(self, p):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT event,object_id,at FROM audit WHERE user_id=? AND tenant_id=? ORDER BY seq", self.scope(p))]

    def raw(self, p, cid, resource, body, now):
        self.connection(p,cid)
        digest = hashlib.sha256(body).hexdigest()
        rid = hashlib.sha256(json_text([*self.scope(p),cid,resource,digest]).encode()).hexdigest()
        with self.lock, self.db:
            self.db.execute("INSERT OR IGNORE INTO receipts VALUES (?,?,?,?,?,?,?,?)", (rid,*self.scope(p),cid,resource,digest,body,aware(now).isoformat()))
            self.receipt(p,rid)
        return rid

    def receipt(self, p, rid):
        with self.lock:
            row=self.db.execute("SELECT * FROM receipts WHERE user_id=? AND tenant_id=? AND id=?", (*self.scope(p),rid)).fetchone()
            if row is None:
                raise PlatformError("NOT_FOUND")
            out=dict(row)
            if hashlib.sha256(out['body']).hexdigest()!=out['sha256']:
                raise PlatformError("PROVENANCE_FAILED")
            expected=hashlib.sha256(json_text([*self.scope(p),out['connection_id'],out['resource'],out['sha256']]).encode()).hexdigest()
            if expected!=out['id']:
                raise PlatformError("PROVENANCE_FAILED")
            return out

    def start_run(self, p,cid,now):
        self.connection(p,cid)
        rid=uuid4().hex
        with self.lock,self.db:
            self.db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)", (rid,*self.scope(p),cid,"RUNNING",aware(now).isoformat(),None,None))
            self.event(p,"SYNC_STARTED",rid,now)
        return rid

    def finish_run(self,p,rid,state,now,error=None):
        if state not in {"PARTIAL","SUCCEEDED","FAILED","REVOKED"}:
            raise PlatformError("INVALID_SYNC_STATE")
        self.run(p,rid)
        with self.lock,self.db:
            self.db.execute("UPDATE runs SET state=?,completed_at=?,error_code=? WHERE user_id=? AND tenant_id=? AND id=?", (state,aware(now).isoformat(),error,*self.scope(p),rid))
            self.event(p,"SYNC_COMPLETED" if state=="SUCCEEDED" else "SYNC_FAILED",rid,now)

    def run(self,p,rid):
        with self.lock:
            row=self.db.execute("SELECT * FROM runs WHERE user_id=? AND tenant_id=? AND id=?", (*self.scope(p),rid)).fetchone()
            if row is None:
                raise PlatformError("NOT_FOUND")
            return dict(row)

    def last_run(self,p,cid,decision_time):
        self.connection(p,cid)
        dt=aware(decision_time)
        with self.lock:
            rows=self.db.execute("SELECT * FROM runs WHERE user_id=? AND tenant_id=? AND connection_id=? ORDER BY rowid DESC", (*self.scope(p),cid)).fetchall()
            for row in rows:
                if aware(row['started_at'])<=dt:
                    result=dict(row)
                    if row['completed_at'] is not None and aware(row['completed_at'])>dt:
                        result.update(state='RUNNING',completed_at=None,error_code=None)
                    return result
            return None

    @staticmethod
    def record_hash(row):
        return hashlib.sha256(json_text({k:row[k] for k in ('user_id','tenant_id','connection_id','resource','object_id','revision','account_id','effective_at','available_at','receipt_id','payload')}).encode()).hexdigest()

    def snapshot_hash(self,p,cid,available_at,payload):
        return hashlib.sha256(json_text([*self.scope(p),cid,available_at,payload]).encode()).hexdigest()

    def cursor(self,p,cid,resource):
        self.connection(p,cid)
        with self.lock:
            row=self.db.execute("SELECT value FROM cursors WHERE user_id=? AND tenant_id=? AND connection_id=? AND resource=?", (*self.scope(p),cid,resource)).fetchone()
            return row['value'] if row else None

    def records(self,p,cid,resource,decision_time,history=False):
        self.connection(p,cid)
        dt=aware(decision_time)
        with self.lock:
            rows=self.db.execute("SELECT * FROM records WHERE user_id=? AND tenant_id=? AND connection_id=? AND resource=? ORDER BY revision,seq", (*self.scope(p),cid,resource)).fetchall()
            eligible=[]
            for row in rows:
                r=dict(row)
                if self.record_hash(r)!=r['sha256']:
                    raise PlatformError("PROVENANCE_FAILED")
                if aware(r['available_at'])<=dt and aware(r['effective_at'])<=dt:
                    self.receipt(p,r['receipt_id'])
                    eligible.append(r)
            if history:
                return eligible
            latest={r['object_id']:r for r in eligible}
            return list(latest.values())

    def commit_records(self,p,cid,normalized,cursors,snapshot=None,now=None):
        self.connection(p,cid)
        with self.lock,self.db:
            for r in normalized:
                old=self.db.execute("SELECT * FROM records WHERE user_id=? AND tenant_id=? AND connection_id=? AND resource=? AND object_id=? AND revision=?", (*self.scope(p),cid,r['resource'],r['object_id'],r['revision'])).fetchone()
                payload=json_text(r['payload'])
                if old is not None and self.record_hash(dict(old))!=old['sha256']:
                    raise PlatformError("PROVENANCE_FAILED")
                if old is not None and old['payload']!=payload:
                    raise PlatformError("REVISION_COLLISION")
                latest=self.db.execute("SELECT MAX(revision) AS revision FROM records WHERE user_id=? AND tenant_id=? AND connection_id=? AND resource=? AND object_id=?", (*self.scope(p),cid,r['resource'],r['object_id'])).fetchone()
                if latest['revision'] is not None and r['revision']<latest['revision']:
                    raise PlatformError("REVISION_REGRESSION")
                raw=self.receipt(p,r['receipt_id'])
                if raw['connection_id']!=cid or raw['resource']!=r['resource']:
                    raise PlatformError("PROVENANCE_FAILED")
                values=(*self.scope(p),cid,r['resource'],r['object_id'],r['revision'],r['account_id'],r['effective_at'],r['available_at'],r['receipt_id'],payload)
                hash_row=dict(zip(('user_id','tenant_id','connection_id','resource','object_id','revision','account_id','effective_at','available_at','receipt_id','payload'),values))
                self.db.execute("INSERT OR IGNORE INTO records(user_id,tenant_id,connection_id,resource,object_id,revision,account_id,effective_at,available_at,receipt_id,payload,sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (*values,self.record_hash(hash_row)))
            for resource,value in cursors.items():
                self.db.execute("INSERT INTO cursors VALUES (?,?,?,?,?) ON CONFLICT(user_id,tenant_id,connection_id,resource) DO UPDATE SET value=excluded.value", (*self.scope(p),cid,resource,value))
            if snapshot is not None:
                payload=json_text(snapshot)
                stamp=aware(now).isoformat()
                self.db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)", (uuid4().hex,*self.scope(p),cid,stamp,payload,self.snapshot_hash(p,cid,stamp,payload)))

    def save_snapshot(self,p,cid,payload,now):
        self.connection(p,cid)
        sid=uuid4().hex
        with self.lock,self.db:
            body=json_text(payload)
            stamp=aware(now).isoformat()
            self.db.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)", (sid,*self.scope(p),cid,stamp,body,self.snapshot_hash(p,cid,stamp,body)))
        return sid

    def latest_snapshot(self,p,cid,decision_time):
        self.connection(p,cid)
        dt=aware(decision_time)
        with self.lock:
            rows=self.db.execute("SELECT * FROM snapshots WHERE user_id=? AND tenant_id=? AND connection_id=? ORDER BY rowid DESC", (*self.scope(p),cid)).fetchall()
            for r in rows:
                if self.snapshot_hash(p,cid,r['available_at'],r['payload'])!=r['sha256']:
                    raise PlatformError("PROVENANCE_FAILED")
                if aware(r['available_at'])<=dt:
                    data=json.loads(r['payload'])
                    for rid in data.get('receipt_ids',[]):
                        self.receipt(p,rid)
                    return {"snapshot_id":r['id'],**data}
            return None
