import sqlite3
from datetime import datetime, timedelta

DB_FILE = "sizes.db"


def get_connection():
    connection = sqlite3.connect(DB_FILE, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_date TEXT NOT NULL,
                coin TEXT NOT NULL,
                direction TEXT NOT NULL,
                size_price REAL NOT NULL,
                extremum_price REAL NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                current_price REAL NOT NULL,
                distance REAL NOT NULL,
                size_vs_max_neighbor REAL NOT NULL,
                size_vs_avg_volume REAL NOT NULL,
                continuous_counter INTEGER NOT NULL DEFAULT 1,
                total_counter INTEGER NOT NULL DEFAULT 1,
                removals INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                ever_crossed INTEGER NOT NULL DEFAULT 0,
                UNIQUE(signal_date, coin, size_price, direction)
            )
        """)
        connection.commit()
    finally:
        connection.close()


def calculate_crossed(direction: str, current_price: float, size_price: float) -> bool:
    if direction == "up":
        return current_price > size_price
    return current_price < size_price


def calculate_distance(size_price: float, current_price: float, direction: str) -> float:
    if direction == "up":
        distance = ((size_price - current_price) / (max(size_price, current_price) / 100))
    else:
        distance = ((current_price - size_price) / (min(size_price, current_price) / 100))

    round_precision = 2 if distance >= 0 else 1
    return round(distance, round_precision)


def save_sizes(coin: str, detected_sizes: list, current_price: float):
    now = datetime.now()
    signal_date = now.strftime("%Y-%m-%d")
    now_string = now.isoformat(timespec="seconds")

    connection = get_connection()

    try:
        detected_keys = set()

        for size in detected_sizes:
            size_price = size["price"]
            direction = size["direction"]
            extremum_price = size["extremum_price"]
            size_vs_max_neighbor = size["size_vs_max_neighbor"]
            size_vs_avg_volume = size["size_vs_avg_volume"]

            key = (coin, size_price, direction)
            detected_keys.add(key)

            crossed = calculate_crossed(
                direction,
                current_price,
                size_price
            )

            cursor = connection.execute("""
                SELECT
                    id,
                    active,
                    ever_crossed,
                    continuous_counter,
                    total_counter
                FROM sizes
                WHERE signal_date = ?
                  AND coin = ?
                  AND size_price = ?
                  AND direction = ?
            """, (
                signal_date,
                coin,
                size_price,
                direction
            ))

            existing = cursor.fetchone()

            if existing is None:
                connection.execute("""
                    INSERT INTO sizes (
                        signal_date,
                        coin,
                        direction,
                        size_price,
                        extremum_price,
                        first_seen,
                        last_seen,
                        current_price,
                        distance,
                        size_vs_max_neighbor,
                        size_vs_avg_volume,
                        continuous_counter,
                        total_counter,
                        removals,
                        active,
                        ever_crossed
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal_date,
                    coin,
                    direction,
                    size_price,
                    extremum_price,
                    now_string,
                    now_string,
                    current_price,
                    calculate_distance(
                        size_price,
                        current_price,
                        direction
                    ),
                    size_vs_max_neighbor,
                    size_vs_avg_volume,
                    1,
                    1,
                    0,
                    1,
                    int(crossed)
                ))

            else:
                if existing["active"]:
                    continuous_counter = existing["continuous_counter"] + 1
                    total_counter = existing["total_counter"] + 1
                    removals = None

                else:
                    continuous_counter = 1
                    total_counter = existing["total_counter"] + 1
                    removals = 1

                if removals is None:
                    connection.execute("""
                        UPDATE sizes
                        SET
                            extremum_price = ?,
                            last_seen = ?,
                            current_price = ?,
                            distance = ?,
                            size_vs_max_neighbor = ?,
                            size_vs_avg_volume = ?,
                            continuous_counter = ?,
                            total_counter = ?,
                            active = 1,
                            ever_crossed = ?
                        WHERE id = ?
                    """, (
                        extremum_price,
                        now_string,
                        current_price,
                        calculate_distance(
                            size_price,
                            current_price,
                            direction
                        ),
                        size_vs_max_neighbor,
                        size_vs_avg_volume,
                        continuous_counter,
                        total_counter,
                        int(existing["ever_crossed"] or crossed),
                        existing["id"]
                    ))

                else:
                    connection.execute("""
                        UPDATE sizes
                        SET
                            extremum_price = ?,
                            last_seen = ?,
                            current_price = ?,
                            distance = ?,
                            size_vs_max_neighbor = ?,
                            size_vs_avg_volume = ?,
                            continuous_counter = ?,
                            total_counter = ?,
                            removals = removals + 1,
                            active = 1,
                            ever_crossed = ?
                        WHERE id = ?
                    """, (
                        extremum_price,
                        now_string,
                        current_price,
                        calculate_distance(
                            size_price,
                            current_price,
                            direction
                        ),
                        size_vs_max_neighbor,
                        size_vs_avg_volume,
                        continuous_counter,
                        total_counter,
                        int(existing["ever_crossed"] or crossed),
                        existing["id"]
                    ))

        cursor = connection.execute("""
            SELECT
                id,
                coin,
                size_price,
                direction,
                active,
                ever_crossed
            FROM sizes
            WHERE signal_date = ?
              AND coin = ?
        """, (
            signal_date,
            coin
        ))

        existing_rows = cursor.fetchall()

        for row in existing_rows:
            key = (
                row["coin"],
                row["size_price"],
                row["direction"]
            )

            if key in detected_keys:
                continue

            if not row["active"]:
                continue

            connection.execute("""
                UPDATE sizes
                SET
                    active = 0,
                    continuous_counter = 0
                WHERE id = ?
            """, (
                row["id"],
            ))

        connection.commit()

    finally:
        connection.close()


def get_sizes():
    connection = get_connection()

    try:
        cursor = connection.execute("""
            SELECT
                id,
                signal_date,
                coin,
                direction,
                size_price,
                extremum_price,
                current_price,
                distance,
                size_vs_max_neighbor,
                size_vs_avg_volume,
                first_seen,
                last_seen,
                continuous_counter,
                total_counter,
                removals,
                active,
                ever_crossed
            FROM sizes
            ORDER BY
                signal_date DESC,
                first_seen DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


def cleanup_old_records(limit=1000):
    """
    Keeps only the newest `limit` records.

    Example:
        cleanup_old_records()
    """
    connection = get_connection()

    try:
        connection.execute("""
            DELETE FROM sizes
            WHERE id NOT IN (
                SELECT id
                FROM sizes
                ORDER BY id DESC
                LIMIT ?
            )
        """, (limit,))

        connection.commit()

    finally:
        connection.close()


def reset_stale_continuous_counters(minutes=5):
    cutoff = datetime.now() - timedelta(minutes=minutes)

    connection = get_connection()

    try:
        connection.execute("""
            UPDATE sizes
            SET continuous_counter = 0
            WHERE continuous_counter > 0
              AND last_seen < ?
        """, (
            cutoff.isoformat(timespec="seconds"),
        ))

        connection.commit()

    finally:
        connection.close()