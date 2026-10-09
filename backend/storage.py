import sqlite3
import threading
from datetime import datetime
from pathlib import Path

# 历史记录存 sqlite，路径锚定在 backend/ 自身（见 storage.HISTORY_DB），所以不管
# 从仓库根跑 `uvicorn backend.main:app` 还是在 backend/ 里跑 `uvicorn main:app`，
# 读写的都是同一个库文件。
HISTORY_DB = Path(__file__).resolve().parent / "history.sqlite3"

# 前端和后端都用这个上限拦超长文本（见 components/InputCard.jsx）
MAX_TEXT_LENGTH = 1000

# analyze 是同步 def，FastAPI 会把它丢进线程池并发执行；sqlite 连接不能跨线程
# 复用，所以每个操作各开各的连接，写操作再串行化，避免并发写互相打断。
_write_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                text TEXT NOT NULL,
                score REAL NOT NULL,
                label TEXT NOT NULL,
                pinyin TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # 兼容已有旧库结构：若无 session_id 列则自动增补
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(history)").fetchall()]
        if "session_id" not in cols:
            conn.execute("ALTER TABLE history ADD COLUMN session_id TEXT")

        # created_at 存的是定长本地 ISO 串（2026-10-08T11:05:43），字典序 == 时间序，
        # 所以直接给这一列建索引，按时间排序/取某天某段时间就都能走索引。IF NOT EXISTS
        # 保证老库也能补上这个索引。
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_created_at ON history (created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_session_id ON history (session_id)"
        )
        _strip_utc_suffix(conn)
        conn.commit()
    finally:
        conn.close()


def _strip_utc_suffix(conn):
    # created_at 现在存本地时间、不带时区尾巴（见 main.py）。老记录是 UTC 且带
    # "+00:00"，这里换算成本地时间再去掉后缀。靠这条 LIKE 兜底，跑过一次后就再也
    # 匹配不到了，所以可以安全重复执行。
    rows = conn.execute(
        "SELECT id, created_at FROM history WHERE created_at LIKE '%+00:00'"
    ).fetchall()
    for row in rows:
        try:
            dt = datetime.fromisoformat(row["created_at"])
        except ValueError:
            continue
        conn.execute(
            "UPDATE history SET created_at = ? WHERE id = ?",
            (dt.astimezone().replace(tzinfo=None).isoformat(timespec="seconds"), row["id"]),
        )


def save_record(record, session_id=None):
    with _write_lock:
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO history (session_id, text, score, label, pinyin, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    record["text"],
                    record["score"],
                    record["label"],
                    record["pinyin"],
                    record["created_at"],
                ),
            )
            conn.commit()
        finally:
            conn.close()


def history(limit=None, session_id=None):
    # id 是自增的，ORDER BY id DESC 就等价于"最新的在前"；新库不再有 order by 反转问题
    # sqlite 里 LIMIT 为负数表示不限条数，所以 limit=None 时映射成 -1 取全部
    if limit is None:
        limit = -1
    conn = get_conn()
    try:
        if session_id is not None:
            rows = conn.execute(
                "SELECT id, session_id, text, score, label, pinyin, created_at FROM history WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, session_id, text, score, label, pinyin, created_at FROM history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]
