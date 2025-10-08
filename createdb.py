import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_NAME = "college"
DB_USER = "postgres"
DB_PASSWORD = "sujit"
DB_HOST = "localhost"
DB_PORT = "5432"

def create_database():
    try:
        # connect to postgres default database
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # check if db exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DB_NAME,))
        exists = cur.fetchone()

        if not exists:
            cur.execute(f"CREATE DATABASE {DB_NAME};")
            print(f"Database '{DB_NAME}' created successfully")
        else:
            print(f"Database '{DB_NAME}' already exists")

        cur.close()
        conn.close()
    except Exception as e:
        print("Error creating database:", e)

if __name__ == "__main__":
    create_database()
