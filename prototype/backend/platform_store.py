"""Row-based platform storage alongside the legacy intelligence state.

All writes use the HTTP handler's connection/transaction, including events.
"""
import json
from copy import deepcopy


def initialize(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    connection.execute('CREATE TABLE IF NOT EXISTS platform_records(entity TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(entity,id))')
    connection.execute('INSERT OR IGNORE INTO schema_migrations(version) VALUES(3)')


def load(connection, state):
    platform = {}
    for entity, body in connection.execute('SELECT entity,body FROM platform_records ORDER BY rowid'):
        platform.setdefault(entity, []).append(json.loads(body))
    if platform:
        state['platform'] = platform
    return state


def save(connection, state):
    platform = state.get('platform', {})
    existing = {(e, i): b for e, i, b in connection.execute('SELECT entity,id,body FROM platform_records')}
    wanted = set()
    for entity, rows in platform.items():
        for row in rows:
            key = (entity, row['id'])
            wanted.add(key)
            body = json.dumps(row, ensure_ascii=False, separators=(',', ':'))
            if existing.get(key) != body:
                connection.execute('INSERT INTO platform_records(entity,id,body) VALUES(?,?,?) ON CONFLICT(entity,id) DO UPDATE SET body=excluded.body', (*key, body))
    for key in existing.keys() - wanted:
        connection.execute('DELETE FROM platform_records WHERE entity=? AND id=?', key)
    legacy = {k: v for k, v in state.items() if k != 'platform'}
    connection.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(legacy, ensure_ascii=False),))

