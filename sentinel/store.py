"""SQLite transaction boundary: proposals, review decisions and simulated ledger."""
import json
import sqlite3
import time
from pathlib import Path

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, state TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, event TEXT, actor TEXT, at REAL);
            CREATE TABLE IF NOT EXISTS ledger(case_id TEXT PRIMARY KEY, amount_minor INTEGER NOT NULL, currency TEXT NOT NULL);
            ''')
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db
    def create(self, case):
        with self.connect() as db:
            db.execute('INSERT INTO cases VALUES(?,?,?,?)', (case['id'], 'investigating', 1, json.dumps(case)))
            db.execute('INSERT INTO audit(case_id,event,actor,at) VALUES(?,?,?,?)',(case['id'],'investigation_started','operator',time.time()))
    def finish(self, id, result, state='awaiting_approval'):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM cases WHERE id=?',(id,)).fetchone()
            case = json.loads(row[0]); case.update(result)
            db.execute('UPDATE cases SET payload=?, state=?, version=version+1 WHERE id=?',(json.dumps(case),state,id))
            db.execute('INSERT INTO audit(case_id,event,actor,at) VALUES(?,?,?,?)',(id,state,'workflow',time.time()))
    def get(self, id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM cases WHERE id=?',(id,)).fetchone()
            if not row: raise KeyError(id)
            case = json.loads(row['payload'])
            case.update(state=row['state'], version=row['version'])
            case['audit'] = [dict(x) for x in db.execute('SELECT event,actor,at FROM audit WHERE case_id=? ORDER BY seq',(id,))]
            case['ledger_entries'] = db.execute('SELECT COUNT(*) FROM ledger WHERE case_id=?',(id,)).fetchone()[0]
            return case
    def all(self):
        with self.connect() as db: ids = [r[0] for r in db.execute('SELECT id FROM cases ORDER BY rowid DESC LIMIT 50')]
        return [self.get(id) for id in ids]
    def decide(self, id, version, decision, actor):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM cases WHERE id=?',(id,)).fetchone()
            if not row: raise KeyError(id)
            if row['state'] != 'awaiting_approval' or row['version'] != version:
                raise ValueError('Stale or already reviewed proposal. Refresh the case.')
            case = json.loads(row['payload'])
            if time.time() > case['expires_at']: raise ValueError('Proposal expired. Start a new investigation.')
            state = 'rejected'
            if decision == 'approve':
                if not case['eligible']: raise ValueError('Policy blocks this adjustment.')
                db.execute('INSERT INTO ledger VALUES(?,?,?)',(id,case['adjustment_minor'],case['currency']))
                state = 'executed_simulation'
            db.execute('UPDATE cases SET state=?,version=version+1 WHERE id=?',(state,id))
            db.execute('INSERT INTO audit(case_id,event,actor,at) VALUES(?,?,?,?)',(id,state,actor,time.time()))
        return self.get(id)
