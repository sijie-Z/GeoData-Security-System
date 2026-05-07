import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1',
    port=5432,
    dbname='esri_test',
    user='postgres',
    password='root',
)

try:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname='public'
          AND tablename LIKE '_bak_20260320_%'
        ORDER BY tablename
        """
    )
    tabs = [r[0] for r in cur.fetchall()]

    for t in tabs:
        cur.execute(f'DROP TABLE IF EXISTS public."{t}" CASCADE')

    conn.commit()
    print(f'DROPPED {len(tabs)}')
    for t in tabs:
        print(f' - {t}')
finally:
    conn.close()
