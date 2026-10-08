"""翻看 sqlite 里的历史记录。

它不自己拼 SQL，而是复用 storage 那一层（history() / init_db()），这样"看记录"
和"存记录"永远读的是同一个库、同一套字段，改了表结构也不用回来改这个脚本。

用法（两种跑法都行）：
    python backend/show_history.py            # 全部记录，最新的在最上面
    python backend/show_history.py -n 5       # 只看最近 5 条
    python backend/show_history.py --json     # 带缩进的 JSON，方便管道给别的命令
    cd backend && python show_history.py
"""

import argparse
import json
import unicodedata

# 和 main.py 一样的双导入兜底：从仓库根跑 `python backend/show_history.py` 时本级
# 是包，走相对导入；在 backend/ 里跑 `python show_history.py` 时没有包可相对，
# 只能直接 import storage。谁在跑谁生效。
try:
    from .storage import history as load_history
except ImportError:
    from storage import history as load_history


def _truncate(value, width):
    # 文本和拼音可能很长，按字符数截断并补省略号，保证表格每列宽度稳定
    value = str(value)
    if _display_width(value) <= width:
        return value
    out = ""
    for ch in value:
        if _display_width(out + ch) > width - 1:
            break
        out += ch
    return out + "…"


def _display_width(value):
    # 中文/全角字符在终端占两格，str.ljust 只按字符数补空格会对不齐，
    # 所以用东亚字符宽度（W/F 记 2，其余记 1）算出真实占位宽度
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in str(value))


def _pad(value, width):
    value = str(value)
    return value + " " * max(width - _display_width(value), 0)


def _short_time(value):
    # created_at 存的是 UTC 的 ISO 串（见 main.py，形如 2026-10-08T03:05:43+00:00）。
    # 表格里末尾的 +00:00 纯属噪音，去掉它；万一将来存了别的时区就原样保留。
    text = str(value)
    if text.endswith("+00:00"):
        text = text[: -len("+00:00")]
    return text


def print_table(records):
    if not records:
        print("（还没有任何记录）")
        return
    # 定好每列宽度，用 ljust 手排（够用，不引第三方库）
    columns = [
        ("id", 4, lambda r: r["id"]),
        ("score", 6, lambda r: r["score"]),
        ("label", 7, lambda r: r["label"]),
        ("text", 24, lambda r: r["text"]),
        ("pinyin", 32, lambda r: r["pinyin"]),
        ("created_at", 19, lambda r: _short_time(r["created_at"])),
    ]
    header = "  ".join(_pad(name, width) for name, width, _ in columns)
    print(header)
    print("-" * _display_width(header))
    for r in records:
        print("  ".join(_pad(_truncate(get(r), width), width) for _, width, get in columns))
    print(f"\n共 {len(records)} 条")


def main():
    parser = argparse.ArgumentParser(description="打印 sqlite 历史记录（最新的在前）")
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="只显示最近 N 条，默认全部",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON（带缩进），方便接给别的命令",
    )
    args = parser.parse_args()

    # limit=None 由 storage.history() 映射成 sqlite 的"不限条数"
    records = load_history(args.limit)

    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        print_table(records)


if __name__ == "__main__":
    main()
