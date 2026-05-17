import sqlite3
import csv

db_path = "D:/experiment/gcsx/lvxin/LX_SkyRoam_Agent/database/sqlite_tables.db"

print(f"连接数据库: {db_path}")
conn = sqlite3.connect(db_path)

# 查看 xhs_note 表的所有列
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(xhs_note)")
columns = cursor.fetchall()
print("\nxhs_note 表的列:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# 导出包含 desc 字段的数据
print("\n导出笔记数据（包含 desc 字段）...")
cursor.execute("""
    SELECT 
        note_id, title, desc, liked_count, collected_count, 
        comment_count, share_count, tag_list, source_keyword, time
    FROM xhs_note
""")
notes = cursor.fetchall()

if notes:
    with open('xhs_notes_full.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['note_id', 'title', 'desc', 'like_count', 'collect_count', 
                        'comment_count', 'share_count', 'tags', 'source_keyword', 'publish_time'])
        for row in notes:
            row_clean = [str(r) if r is not None else '' for r in row]
            writer.writerow(row_clean)
    print(f"✅ 导出 {len(notes)} 条笔记到 xhs_notes_full.csv")
    
    # 显示样例
    print("\n样例数据:")
    print(f"  title: {notes[0][1][:50] if notes[0][1] else '无'}")
    print(f"  desc: {notes[0][2][:100] if notes[0][2] else '无'}...")
else:
    print("⚠️ 笔记表为空")

conn.close()
