import datetime
import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1',
    port=5432,
    dbname='esri_test',
    user='postgres',
    password='root',
)
cur = conn.cursor()

cur.execute("select tablename from pg_tables where schemaname='public'")
tables = [r[0] for r in cur.fetchall()]
table_map = {t.lower(): t for t in tables}

keep = {'shp_data', 'raster_data', 'spatial_ref_sys'}
candidates = {
    'applications', 'download_records', 'extract_helpers', 'embed_file_records',
    'send_file_records', 'system_logs', 'user_notifications',
    'shpstore', 'shpdataio', 'road', 'waterway', 'coastline'
}

today = datetime.datetime.now().strftime('%Y%m%d')
renamed = []
skipped = []

for c in sorted(candidates):
    if c in keep:
        continue

    if c in table_map:
        src = table_map[c]
        dst = f'_bak_{today}_{src.lower()}'
        if dst in table_map:
            skipped.append((src, 'target_exists'))
        else:
            cur.execute(f'ALTER TABLE public."{src}" RENAME TO "{dst}"')
            renamed.append((src, dst))
    else:
        skipped.append((c, 'not_found'))

conn.commit()

print('RENAMED:')
for a, b in renamed:
    print(f'  {a} -> {b}')

print('SKIPPED:')
for a, reason in skipped:
    print(f'  {a} ({reason})')

cur.close()
conn.close()
