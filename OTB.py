# E:\club_checkin\db.py
import psycopg2
import psycopg2.extras

DB = {
    "port":"30004",
    "host": "192.168.22.130",
    "user": "opentenbase",
    "password": "123456",
    "dbname": "postgres",
}

def Query(sql, args=None):
    """查：返回 list[dict]，查不到就是 []"""
    conn = psycopg2.connect(**DB)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, args or ())
        return cur.fetchall()
    finally:
        conn.close()

def Execute(sql, args=None):
    """增删改：返回受影响行数"""
    conn = psycopg2.connect(**DB)
    try:
        cur = conn.cursor()
        cur.execute(sql, args or ())
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
