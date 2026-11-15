"""Creates the database and tables.  Run once:  python init_db.py"""
import mysql.connector
from config import Config, BASE_DIR
import os

conn = mysql.connector.connect(
    host=Config.MYSQL_HOST, user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD
)
cur = conn.cursor()
cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cur.execute(f"USE `{Config.MYSQL_DB}`")

with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
    sql = "\n".join(l for l in f.read().splitlines() if not l.strip().startswith("--"))

for stmt in sql.split(";"):
    if stmt.strip():
        cur.execute(stmt)
conn.commit()
cur.close()
conn.close()
print(f"✅ Database '{Config.MYSQL_DB}' is ready (users, contacts, sos_logs).")
