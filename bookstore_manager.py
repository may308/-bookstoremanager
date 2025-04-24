import sqlite3
from typing import Tuple


def connect_db() -> sqlite3.Connection:
    """建立並返回 SQLite 資料庫連線"""
    conn = sqlite3.connect('bookstore.db')
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    """初始化資料庫：建立資料表並插入初始資料"""
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

            INSERT OR IGNORE INTO sale (
                sid, sdate, mid, bid, sqty, sdiscount, stotal
            )
            VALUES (1, '2024-01-15', 'M001', 'B001', 2, 100, 1100);
            INSERT OR IGNORE INTO sale (
                sid, sdate, mid, bid, sqty, sdiscount, stotal
            )
            VALUES (2, '2024-01-16', 'M002', 'B002', 1, 50, 750);
            INSERT OR IGNORE INTO sale (
                sid, sdate, mid, bid, sqty, sdiscount, stotal
            )
            VALUES (3, '2024-01-17', 'M001', 'B003', 3, 200, 3400);
            INSERT OR IGNORE INTO sale (
                sid, sdate, mid, bid, sqty, sdiscount, stotal
            )
            VALUES (4, '2024-01-18', 'M003', 'B001', 1, 0, 600);
            """
        )


def add_sale(
    conn: sqlite3.Connection,
    sdate: str,
    mid: str,
    bid: str,
    sqty: int,
    sdiscount: int
) -> Tuple[bool, str]:
    """新增銷售記錄，驗證會員、書籍、數量、折扣等"""
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
            "INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sdate, mid, bid, sqty, sdiscount, stotal),
        )
        cursor.execute(
            "UPDATE book SET bstock = bstock - ? WHERE bid = ?",
            (sqty, bid)
        )
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
        SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice,
               s.sqty, s.sdiscount, s.stotal
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
            f"{sale['bprice']}\t{sale['sqty']}\t"
            f"{sale['sdiscount']}\t{sale['stotal']:,}"
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
            "SELECT sqty, b.bprice "
            "FROM sale s "
            "JOIN book b ON s.bid = b.bid "
            "WHERE sid = ?",
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


def delete_sale(conn: sqlite3.Connection) -> None:
    """刪除指定銷售記錄"""
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

    while True:

        sid_input = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ")
        if not sid_input:
            return
        try:
            sid = int(sid_input)
            if sid < 1 or sid > len(sales):
                print("錯誤：請輸入有效的數字")
                continue
            sid_val = sales[sid - 1]["sid"]
            cursor.execute("DELETE FROM sale WHERE sid = ?", (sid_val,))
            conn.commit()
            print(f"=> 銷售編號 {sid_val} 已刪除")
            break
        except ValueError:
            print("錯誤：請輸入有效的數字")


def main() -> None:
    """主程式：選單迴圈與功能呼叫"""
    conn = connect_db()
    initialize_db(conn)

    while True:
        print("\n***************選單***************")
        print("1. 新增銷售記錄")
        print("2. 顯示銷售報表")
        print("3. 更新銷售記錄")
        print("4. 刪除銷售記錄")
        print("5. 離開")
        print("**********************************")
        choice = input("請選擇操作項目(Enter 離開)：")
        if choice == "" or choice == "5":
            print("再見！")
            break
        elif choice == "1":
            sdate = input("請輸入銷售日期 (YYYY-MM-DD)：")
            mid = input("請輸入會員編號：")
            bid = input("請輸入書籍編號：")

            # 數量輸入與驗證
            while True:
                try:
                    sqty_input = input("請輸入購買數量：")
                    sqty = int(sqty_input)
                    if sqty <= 0:
                        print("=> 錯誤：數量必須為正整數，請重新輸入")
                        continue
                    break
                except ValueError:
                    print("=> 錯誤：數量必須為整數，請重新輸入")

            # 折扣金額輸入與驗證
            while True:
                try:
                    sdiscount_input = input("請輸入折扣金額：")
                    sdiscount = int(sdiscount_input)
                    if sdiscount < 0:
                        print("=> 錯誤：折扣金額不能為負數，請重新輸入")
                        continue
                    break
                except ValueError:
                    print("=> 錯誤：折扣金額必須為整數，請重新輸入")

            # 呼叫新增銷售記錄的函式
            success, message = add_sale(conn, sdate, mid, bid, sqty, sdiscount)
            print(f"=> {message}")
        elif choice == "2":
            print_sale_report(conn)
        elif choice == "3":
            update_sale(conn)
        elif choice == "4":
            delete_sale(conn)
        else:
            print("=> 請輸入有效的選項（1-5）")


if __name__ == "__main__":
    main()
