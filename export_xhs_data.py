
import sqlite3
import csv
import os

# 直接指定数据库路径
db_path = "D:/experiment/gcsx/lvxin/LX_SkyRoam_Agent/database/sqlite_tables.db"

print(f"使用数据库: {db_path}")

# 检查文件是否存在
if not os.path.exists(db_path):
    print(f"错误: 数据库文件不存在 - {db_path}")
    exit()

# 连接数据库
conn = sqlite3.connect(db_path)
conn.text_factory = str

# 导出笔记表 (xhs_note)
print("\n📝 导出笔记数据...")
try:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            note_id, title, desc, liked_count, collected_count, 
            comment_count, share_count, tag_list, source_keyword, time
        FROM xhs_note
    """)
    notes = cursor.fetchall()

    if notes:
        with open('xhs_notes.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['note_id', 'title', 'content', 'like_count', 'collect_count', 
                            'comment_count', 'share_count', 'tags', 'source_keyword', 'publish_time'])
            for row in notes:
                row_clean = [str(r) if r is not None else '' for r in row]
                writer.writerow(row_clean)
        print(f"✅ 导出 {len(notes)} 条笔记到 xhs_notes.csv")
    else:
        print("⚠️ 笔记表为空")
except Exception as e:
    print(f"❌ 导出笔记失败: {e}")

# 导出评论表 (xhs_note_comment)
print("\n💬 导出评论数据...")
try:
    cursor.execute("""
        SELECT 
            comment_id, note_id, content, like_count, 
            sub_comment_count, parent_comment_id, nickname, create_time
        FROM xhs_note_comment
    """)
    comments = cursor.fetchall()

    if comments:
        with open('xhs_comments.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['comment_id', 'note_id', 'comment_content', 'like_count', 
                            'sub_comment_count', 'parent_comment_id', 'nickname', 'create_time'])
            for row in comments:
                row_clean = [str(r) if r is not None else '' for r in row]
                writer.writerow(row_clean)
        print(f"✅ 导出 {len(comments)} 条评论到 xhs_comments.csv")
    else:
        print("⚠️ 评论表为空")
except Exception as e:
    print(f"❌ 导出评论失败: {e}")

conn.close()

print("\n✅ 导出完成！")
print("\n生成的文件:")
if os.path.exists('xhs_notes.csv'):
    print("  - xhs_notes.csv    (小红书笔记)")
if os.path.exists('xhs_comments.csv'):
    print("  - xhs_comments.csv (小红书评论)")
