import logging
import time

import psycopg
from django.conf import settings

logger = logging.getLogger(__name__)

TABLE_NAME = 'metatune_visitors'
PAUSE_SECONDS = 60    # after an error the database is not asked for this time (the site stays fast)
CACHE_SECONDS = 30    # the total number is remembered for this time

table_ready = False
paused_until = 0
known_visitors = set()
cached_total = None
cached_time = 0


def connect():
    # prepare_threshold=None is needed for the Supabase connection pooler
    return psycopg.connect(settings.SUPABASE_DB_URL, connect_timeout=5, prepare_threshold=None, autocommit=True)


def make_table(connection):
    # The table is created automatically on the first visit
    global table_ready
    if table_ready:
        return

    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id BIGSERIAL PRIMARY KEY,
            visitor_id TEXT UNIQUE NOT NULL,
            first_visit TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    # Nobody can read the table through the public Supabase API
    connection.execute(f'ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY')
    table_ready = True


def run_query(work):
    """Runs work(connection). Returns None if the database is not set or does not work"""
    global paused_until

    if not settings.SUPABASE_DB_URL or time.time() < paused_until:
        return None

    try:
        with connect() as connection:
            make_table(connection)
            return work(connection)
    except Exception as error:
        paused_until = time.time() + PAUSE_SECONDS
        logger.warning(
            'Supabase is not available (%s: %s). If you use the direct address (db.xxx.supabase.co), '
            'try the Session pooler address from Supabase -> Connect. Check: python manage.py check_setup',
            type(error).__name__, str(error).strip()[:200],
        )
        return None


def count_visitors(connection):
    return connection.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}').fetchone()[0]


def register_visit(visitor_id):
    """Saves a new visitor and returns the total number of visitors (None if the database does not work)"""
    global cached_total, cached_time

    # A known visitor does not need the database every time
    if visitor_id in known_visitors and cached_total is not None and time.time() - cached_time < CACHE_SECONDS:
        return cached_total

    def work(connection):
        if visitor_id not in known_visitors:
            connection.execute(
                f'INSERT INTO {TABLE_NAME} (visitor_id) VALUES (%s) ON CONFLICT (visitor_id) DO NOTHING',
                (visitor_id,),
            )
        return count_visitors(connection)

    total = run_query(work)
    if total is None:
        return cached_total

    known_visitors.add(visitor_id)
    cached_total = total
    cached_time = time.time()
    return total


def get_total():
    return run_query(count_visitors)


def get_visitor_number(visitor_id):
    """Returns the number of the visitor (1 = the first person who visited the site)"""
    if not visitor_id:
        return None

    def work(connection):
        row = connection.execute(f'SELECT id FROM {TABLE_NAME} WHERE visitor_id = %s', (visitor_id,)).fetchone()
        return row[0] if row else None

    return run_query(work)
