import os
import psycopg2
from dotenv import load_dotenv

def main():
    load_dotenv()  # โหลด .env

    host = os.getenv("DB_HOST")
    port = int(os.getenv("DB_PORT", "5432"))
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([host, dbname, user, password]):
        raise ValueError("Missing env vars: DB_HOST/DB_NAME/DB_USER/DB_PASSWORD (and DB_PORT optional)")

    print("Connecting...")

    with psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=5,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT now(), current_user, current_database();")
            now, current_user, current_db = cur.fetchone()

    print("✅ Connected!")
    print("time:", now)
    print("user:", current_user)
    print("db  :", current_db)

if __name__ == "__main__":
    main()