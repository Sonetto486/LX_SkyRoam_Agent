"""临时脚本：添加 image_source 列"""

import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='skyroam',
    user='postgres',
    password='lpy1022'
)

cur = conn.cursor()

# Check if column exists
cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='attraction_details'
    AND column_name='image_source'
""")
result = cur.fetchone()

if result:
    print('Column image_source already exists')
else:
    cur.execute('ALTER TABLE attraction_details ADD COLUMN image_source VARCHAR(50)')
    conn.commit()
    print('Column image_source added successfully')

cur.close()
conn.close()