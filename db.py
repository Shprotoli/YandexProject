import sqlite3


class SQLiteHandler:
    DB_FILE = "system_data.db"

    @staticmethod
    def init_db():
        conn = sqlite3.connect(SQLiteHandler.DB_FILE)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS system_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT,
                cpu REAL,
                memory REAL,
                gpu REAL,
                network_kb REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT UNIQUE,
                setting_value TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS hardware_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_name TEXT,
                gpu_name TEXT,
                ram_size_gb REAL,
                os_name TEXT
            )
        """)

        conn.commit()
        conn.close()

    @staticmethod
    def insert_usage(data):
        conn = sqlite3.connect(SQLiteHandler.DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO system_usage (time, cpu, memory, gpu, network_kb)
            VALUES (?, ?, ?, ?, ?)
        """, (data["time"], data["cpu"], data["memory"], data["gpu"], data["network_kb"]))
        conn.commit()
        conn.close()

    @staticmethod
    def fetch_all_usage():
        conn = sqlite3.connect(SQLiteHandler.DB_FILE)
        c = conn.cursor()
        c.execute("SELECT time, cpu, memory, gpu, network_kb FROM system_usage ORDER BY id")
        rows = c.fetchall()
        conn.close()
        return [{"time": r[0], "cpu": r[1], "memory": r[2], "gpu": r[3], "network_kb": r[4]} for r in rows]

    @staticmethod
    def insert_setting(name, value):
        conn = sqlite3.connect(SQLiteHandler.DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO user_settings (setting_name, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_name) DO UPDATE SET setting_value = excluded.setting_value
        """, (name, value))
        conn.commit()
        conn.close()

    @staticmethod
    def fetch_settings():
        conn = sqlite3.connect(SQLiteHandler.DB_FILE)
        c = conn.cursor()
        c.execute("SELECT setting_name, setting_value FROM user_settings")
        rows = c.fetchall()
        conn.close()
        return [{"name": r[0], "value": r[1]} for r in rows]

    @staticmethod
    def insert_hardware(cpu_name, gpu_name, ram_size_gb, os_name):
        conn = sqlite3.connect(SQLiteHandler.DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO hardware_info (cpu_name, gpu_name, ram_size_gb, os_name)
            VALUES (?, ?, ?, ?)
        """, (cpu_name, gpu_name, ram_size_gb, os_name))
        conn.commit()
        conn.close()

    @staticmethod
    def fetch_hardware():
        conn = sqlite3.connect(SQLiteHandler.DB_FILE)
        c = conn.cursor()
        c.execute("SELECT cpu_name, gpu_name, ram_size_gb, os_name FROM hardware_info")
        rows = c.fetchall()
        conn.close()
        return [{"cpu": r[0], "gpu": r[1], "ram": r[2], "os": r[3]} for r in rows]
