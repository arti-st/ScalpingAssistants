import sqlite3
from datetime import datetime, timedelta

DB_FILE = "sizes.db"


def get_connection():
    connection = sqlite3.connect(DB_FILE, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def create_table():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sizes (
            date TEXT NOT NULL,
            coin TEXT NOT NULL,
            dom REAL,
            chart REAL,
            current_price REAL,
            direction INTEGER,
            distance REAL,
            size_vs_dom REAL,
            size_vs_avg REAL,
            first_signal TEXT NOT NULL,
            last_fixation TEXT NOT NULL,
            continuous_count INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            status INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            coin TEXT PRIMARY KEY,
            tick_size REAL NOT NULL,
            avg_atr REAL NOT NULL,
            status INTEGER NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def create_renew_size(
        coin: str,
        size_price: float,
        chart_price: float | None,
        current_price: float,
        size_dir: int,
        size_dist: float,
        size_vs_dom: float,
        size_vs_avg: float
):
    now = datetime.now()

    date = now.strftime("%d.%m.%y")
    time = now.strftime("%H:%M:%S")

    connection = get_connection()

    cursor = connection.execute("""
        SELECT total_count
        FROM sizes
        WHERE date = ? AND coin = ? AND dom = ?
    """, (date, coin, size_price))

    row = cursor.fetchone()

    if row:
        connection.execute("""
            UPDATE sizes
            SET
                chart = COALESCE(?, chart),
                current_price = ?,
                direction = ?,
                distance = ?,
                size_vs_dom = ?,
                size_vs_avg = ?,
                last_fixation = ?,
                continuous_count = continuous_count + 1,
                total_count = total_count + 1,
                status = CASE WHEN status = 5 THEN 2 ELSE 1 END
            WHERE date = ? AND coin = ? AND dom = ?
        """, (
            chart_price,
            current_price,
            size_dir,
            size_dist,
            size_vs_dom,
            size_vs_avg,
            time,
            date,
            coin,
            size_price
        ))

    else:
        connection.execute("""
            INSERT INTO sizes (
                date,
                coin,
                dom,
                chart,
                current_price,
                direction,
                distance,
                size_vs_dom,
                size_vs_avg,
                first_signal,
                last_fixation,
                continuous_count,
                total_count,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date,
            coin,
            size_price,
            chart_price,
            current_price,
            size_dir,
            size_dist,
            size_vs_dom,
            size_vs_avg,
            time,
            time,
            1,
            1,
            1
        ))

    connection.commit()
    connection.close()


def get_current_sizes(coin):
    today = datetime.now().strftime("%d.%m.%y")

    connection = get_connection()

    cursor = connection.execute("""
        SELECT *
        FROM sizes
        WHERE date = ? AND coin = ? AND status IN (1, 2)
    """, (today, coin))

    rows = cursor.fetchall()

    connection.close()

    return {
        row["dom"]: {
            key: row[key]
            for key in row.keys()
            if key != "dom"
        }
        for row in rows
    }


def get_open_sizes():
    today = datetime.now().strftime("%d.%m.%y")

    connection = get_connection()

    cursor = connection.execute("""
        SELECT coin, dom, direction, distance, continuous_count, total_count
        FROM sizes
        WHERE date = ? AND status = 1
        ORDER BY coin, dom
    """, (today,))

    rows = cursor.fetchall()

    connection.close()

    return rows


def get_all_sizes():
    today = datetime.now().strftime("%d.%m.%y")

    connection = get_connection()

    cursor = connection.execute("""
        SELECT
            date,
            coin,
            dom,
            chart,
            current_price,
            direction,
            distance,
            size_vs_dom,
            size_vs_avg,
            first_signal,
            last_fixation,
            continuous_count,
            total_count,
            status
        FROM sizes
        WHERE date = ?
        ORDER BY
            date DESC,
            CASE status WHEN 1 THEN 1 WHEN 2 THEN 2 WHEN 3 THEN 3
                        WHEN 4 THEN 4 WHEN 5 THEN 5 ELSE 6 END ASC,
            CASE WHEN status IN (1, 2) THEN distance END ASC,
            CASE WHEN status NOT IN (1, 2) THEN last_fixation END DESC
    """, (today,))

    rows = cursor.fetchall()

    connection.close()

    return rows


def change_size_status(coin, dom, status):
    connection = get_connection()

    connection.execute("""
        UPDATE sizes
        SET 
            status = ?,
            continuous_count = 0
        WHERE date = ? AND coin = ? AND dom = ?
    """, (
        status,
        datetime.now().strftime("%d.%m.%y"),
        coin,
        dom
    ))

    connection.commit()
    connection.close()


def unlist_coin_in_sizes(coin):
    connection = get_connection()

    connection.execute("""
        UPDATE sizes
        SET 
            status = 6,
            continuous_count = 0
        WHERE date = ? AND coin = ?
    """, (
        datetime.now().strftime("%d.%m.%y"),
        coin
    ))

    connection.commit()
    connection.close()


def update_unlisted_coins():
    today = datetime.now().strftime("%d.%m.%y")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%y")

    connection = get_connection()

    rows_1 = connection.execute("""
        SELECT coin, status
        FROM coins
        WHERE status = 1
    """).fetchall()

    rows_other = connection.execute("""
        SELECT coin, status
        FROM coins
        WHERE NOT status = 1
    """).fetchall()

    connection.execute("""
        UPDATE sizes
        SET
            status = 6,
            continuous_count = 0
        WHERE date = ?
          AND coin NOT IN (
              SELECT coin
              FROM coins
              WHERE status = 1
          )
    """, (today,))

    connection.execute("""
        DELETE FROM sizes
        WHERE date = ?
    """, (yesterday,))

    connection.commit()
    connection.close()


def is_coin_active(coin: str) -> bool:
    connection = get_connection()

    row = connection.execute("""
        SELECT 1
        FROM coins
        WHERE coin = ? AND status = 1
    """, (coin,)).fetchone()

    connection.close()

    return row is not None


def add_coin_to_coins(coin: str, tick_size: float, avg_atr: float, status: int):
    connection = get_connection()

    connection.execute("""
        INSERT INTO coins (
            coin,
            tick_size,
            avg_atr,
            status
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(coin) DO UPDATE SET
            tick_size = excluded.tick_size,
            avg_atr = excluded.avg_atr,
            status = CASE
                WHEN coins.status IN (0, 1, 2) THEN excluded.status
                ELSE coins.status
            END
    """, (
        coin,
        tick_size,
        avg_atr,
        status
    ))

    connection.commit()
    connection.close()


def set_coin_status(coin: str, status: int):
    """
    1 - active
    2 - auto-ban
    3 - manual-ban
    """
    connection = get_connection()

    connection.execute("""
        UPDATE coins
        SET status = ?
        WHERE coin = ?
    """, (status, coin))

    connection.commit()
    connection.close()


def get_coins():
    connection = get_connection()

    cursor = connection.execute("""
        SELECT coin, tick_size, avg_atr, status
        FROM coins
        WHERE status = 1
    """)

    rows = cursor.fetchall()

    connection.close()

    return {
        row["coin"]: {
            "tick_size": row["tick_size"],
            "avg_atr": row["avg_atr"],
            "status": row["status"]
        }
        for row in rows
    }
