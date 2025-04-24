import sqlite3
from typing import Tuple


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect('bookstore.db')
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    with conn:
        cursor = conn.cursor()
        cursor.executescript(
            """
        CREATE TABLE IF NOT EXISTS member (
            mid TEXT PRIMARY KEY,
            mname TEXT NOT NULL,
            mphone TEXT NOT NULL,
            memail TEXT
        );

        CREATE TABLE IF NOT EXISTS book (
            bid TEXT PRIMARY KEY,
            btitle TEXT NOT NULL,
            bprice INTEGER NOT NULL,
            bstock INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sale (
            sid INTEGER PRIMARY KEY AUTOINCREMENT,
            sdate TEXT NOT NULL,
            mid TEXT NOT NULL,
            bid TEXT NOT NULL,
            sqty INTEGER NOT NULL,
            sdiscount INTEGER NOT NULL,
            stotal INTEGER NOT NULL
        );

        INSERT OR IGNORE INTO member VALUES (
            'M001', 'Alice', '0912-345678', 'alice@example.com'
        );
        INSERT OR IGNORE INTO member VALUES (
            'M002', 'Bob', '0923-456789', 'bob@example.com'
        );
        INSERT OR IGNORE INTO member VALUES (
            'M003', 'Cathy', '0934-567890', 'cathy@example.com'
        );

        INSERT OR IGNORE INTO book VALUES (
            'B001', 'Python Programming', 600, 50
        );
        INSERT OR IGNORE INTO book VALUES (
            'B002', 'Data Science Basics', 800, 30
        );
        INSERT OR IGNORE INTO book VALUES (
            'B003', 'Machine Learning Guide', 1200, 20
        );

        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal)
        VALUES ('2024-01-15', 'M001', 'B001', 2, 100, 1100);
        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal)
        VALUES ('2024-01-16', 'M002', 'B002', 1, 50, 750);
        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal)
        VALUES ('2024-01-17', 'M001', 'B003', 3, 200, 3400);
        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal)
        VALUES ('2024-01-18', 'M003', 'B001', 1, 0, 600);
        """
        )


def add_sale(
    conn: sqlite3.Connection, sdate: str, mid: str, bid: str, sqty: int, sdiscount: int
) -> Tuple[bool, str]:
    try:
        cursor = conn.cursor()

        if len(sdate) != 10 or sdate.count("-") != 2:
            return False, "錯誤：日期格式錯誤，請使用 YYYY-MM-DD"

        cursor.execute("SELECT * FROM member WHERE mid = ?", (mid,))
        if not cursor.fetchone():
            return False, "錯誤：會員編號無效"

        cursor.execute("SELECT * FROM book WHERE bid = ?", (bid,))
        book = cursor.fetchone()
        if not book:
            return False, "錯誤：書籍編號無效"

        if sqty <= 0:
            return False, "錯誤：數量必須為正整數"

        if sdiscount < 0:
            return False, "錯誤：折扣金額不能為負數"

        if sqty > book["bstock"]:
            return False, f"錯誤：書籍庫存不足 (現有庫存: {book['bstock']})"

        stotal = book["bprice"] * sqty - sdiscount

        cursor.execute("BEGIN")
        cursor.execute(
            "INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES (?, ?, ?, ?, ?, ?)",
            (sdate, mid, bid, sqty, sdiscount, stotal),
        )
        cursor.execute("UPDATE book SET bstock = bstock - ? WHERE bid = ?", (sqty, bid))
        conn.commit()
        return True, f"銷售記錄已新增！(銷售總額: {stotal:,})"
    except sqlite3.Error:
        conn.rollback()
        return False, "資料庫錯誤，新增失敗"

def print_sale_report(conn: sqlite3.Connection) -> None:
    """顯示所有銷售記錄的報表"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, s.sqty, s.sdiscount, s.stotal
        FROM sale s
        JOIN member m ON s.mid = m.mid
        JOIN book b ON s.bid = b.bid
        ORDER BY s.sid
    """
    )
    sales = cursor.fetchall()
    for i, sale in enumerate(sales, 1):
        print("\n==================== 銷售報表 ====================")
        print(f"銷售 #{i}")
        print(f"銷售編號: {sale['sid']}")
        print(f"銷售日期: {sale['sdate']}")
        print(f"會員姓名: {sale['mname']}")
        print(f"書籍標題: {sale['btitle']}")
        print("--------------------------------------------------")
        print("單價\t數量\t折扣\t小計")
        print("--------------------------------------------------")
        print(
            f"{sale['bprice']}\t{sale['sqty']}\t{sale['sdiscount']}\t{sale['stotal']:,}"
        )
        print("--------------------------------------------------")
        print(f"銷售總額: {sale['stotal']:,}")
        print("==================================================")


def update_sale(conn: sqlite3.Connection) -> None:
    """更新銷售折扣金額並重算總額"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.sid, s.sdate, m.mname FROM sale s
        JOIN member m ON s.mid = m.mid
        ORDER BY s.sid
    """
    )
    sales = cursor.fetchall()
    print("\n======== 銷售記錄列表 ========")
    for i, s in enumerate(sales, 1):
        print(f"{i}. 銷售編號: {s['sid']} - 會員: {s['mname']} - 日期: {s['sdate']}")
    print("================================")

    sid_input = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ")
    if not sid_input:
        return
    try:
        sid = int(sid_input)
        if sid < 1 or sid > len(sales):
            raise ValueError
        sid_val = sales[sid - 1]["sid"]
        discount = int(input("請輸入新的折扣金額："))
        if discount < 0:
            print("錯誤：折扣金額不能為負數")
            return

        cursor.execute(
            "SELECT sqty, b.bprice FROM sale s JOIN book b ON s.bid = b.bid WHERE sid = ?",
            (sid_val,),
        )
        sale = cursor.fetchone()
        stotal = sale["bprice"] * sale["sqty"] - discount
        cursor.execute(
            "UPDATE sale SET sdiscount = ?, stotal = ? WHERE sid = ?",
            (discount, stotal, sid_val),
        )
        conn.commit()
        print(f"=> 銷售編號 {sid_val} 已更新！(銷售總額: {stotal:,})")
    except (ValueError, IndexError):
        print("錯誤：請輸入有效的數字")


