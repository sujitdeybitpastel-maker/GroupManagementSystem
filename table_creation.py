import psycopg2
from psycopg2 import Error

def create_tables():
    try:
        # Connect to PostgreSQL
        connection = psycopg2.connect(
            host="localhost",        
            user="postgres",         
            password="sujit", 
            database="GroupManagementSystem",
            port="5432"
        )
        connection.autocommit = True
        cursor = connection.cursor()

        # --- Group table ---
        create_group_query = """
        CREATE TABLE IF NOT EXISTS "dashboard_app_group" (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            platform VARCHAR(100) NOT NULL,
            group_type VARCHAR(50) CHECK (group_type IN ('Group', 'Channel', 'Broadcast')) NOT NULL,
            added_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status SMALLINT NOT NULL DEFAULT 1 CHECK (status IN (0, 1, 5))
        );
        """

        # --- Members table ---
        create_members_query = """
        CREATE TABLE IF NOT EXISTS "dashboard_app_members" (
            id BIGSERIAL PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            phone_number VARCHAR(50) UNIQUE,
            email VARCHAR(255) UNIQUE,
            username VARCHAR(100),
            platforms TEXT[] NOT NULL, -- multiple platforms stored as array
            added_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_updated_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status SMALLINT NOT NULL DEFAULT 1 CHECK (status IN (0, 1, 5))
        );
        """

        # --- Messages table ---
        create_messages_query = """
        CREATE TABLE IF NOT EXISTS "dashboard_app_messages" (
            id BIGSERIAL PRIMARY KEY,
            text_body TEXT NOT NULL,
            has_media BOOLEAN DEFAULT FALSE,
            media_url TEXT,
            group_id BIGINT NOT NULL,
            sender_id BIGINT NOT NULL,
            added_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_updated_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status SMALLINT NOT NULL DEFAULT 1 CHECK (status IN (0, 1, 5)),

            -- Foreign Keys
            CONSTRAINT fk_group FOREIGN KEY (group_id) REFERENCES "dashboard_app_group"(id) ON DELETE CASCADE,
            CONSTRAINT fk_sender FOREIGN KEY (sender_id) REFERENCES "dashboard_app_members"(id) ON DELETE CASCADE
        );
        """

        # Execute queries in the correct order
        cursor.execute(create_group_query)
        cursor.execute(create_members_query)
        cursor.execute(create_messages_query)

        print("Tables 'Group', 'Members', and 'Messages' created successfully!")

    except Error as e:
        print(f"Error: {e}")

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection closed.")

if __name__ == "__main__":
    create_tables()
