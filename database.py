
import os
import psycopg
from dotenv import load_dotenv

# Load the connection string from .env
load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL not found in .env")

# Connect to Supabase PostgreSQL
try:
    with psycopg.connect(
        database_url,
        sslmode="require",
        connect_timeout=10
    ) as conn:
        print("Successfully connected to PostgreSQL!")

        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database();")
            result = cursor.fetchone()

            print("Database:", result[0])

except psycopg.Error as error:
    print("Connection failed!")
    print("Error type:", type(error).__name__)
    print("Error details:", str(error))