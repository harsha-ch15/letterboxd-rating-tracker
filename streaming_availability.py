
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def add_streaming_availability(
    movie_slug,
    country_code,
    platform_name,
    availability_type
):
    with psycopg.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    ) as conn:

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO movie_streaming
                (
                    letterboxd_slug,
                    country_code,
                    platform_name,
                    availability_type
                )
                VALUES (%s, %s, %s, %s)

                ON CONFLICT (
                    letterboxd_slug,
                    country_code,
                    platform_name,
                    availability_type
                )
                DO UPDATE SET
                    last_checked = NOW();
            """, (
                movie_slug,
                country_code,
                platform_name,
                availability_type
            ))

            print("Streaming availability saved.")


def check_streaming_changes(movie_slug, country_code, new_platforms):

    # Convert new data into a set
    new_platforms = set(new_platforms)

    with psycopg.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    ) as conn:

        with conn.cursor() as cursor:

            # Lock this movie/country's existing rows
            cursor.execute("""
                SELECT platform_name, availability_type
                FROM movie_streaming
                WHERE letterboxd_slug = %s
                  AND country_code = %s
                FOR UPDATE;
            """, (movie_slug, country_code))

            old_platforms = set(cursor.fetchall())

            # Find differences
            added = new_platforms - old_platforms
            removed = old_platforms - new_platforms

            # Insert newly available platforms
            for platform, availability in added:
                cursor.execute("""
                    INSERT INTO movie_streaming
                    (
                        letterboxd_slug,
                        country_code,
                        platform_name,
                        availability_type
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (
                        letterboxd_slug,
                        country_code,
                        platform_name,
                        availability_type
                    )
                    DO UPDATE SET last_checked = NOW();
                """, (
                    movie_slug,
                    country_code,
                    platform,
                    availability
                ))
                # Log the addition in streaming_change_log
                cursor.execute("""
                    INSERT INTO streaming_change_log
                    (
                        letterboxd_slug,
                        country_code,
                        platform_name,
                        availability_type,
                        change_type
                    )
                    VALUES (%s, %s, %s, %s, %s);
                """, (
                    movie_slug,
                    country_code,
                    platform,
                    availability,
                    "added"
                ))                
                
            # Delete platforms that disappeared
            for platform, availability in removed:
                cursor.execute("""
                    DELETE FROM movie_streaming
                    WHERE letterboxd_slug = %s
                      AND country_code = %s
                      AND platform_name = %s
                      AND availability_type = %s;
                """, (
                    movie_slug,
                    country_code,
                    platform,
                    availability
                ))
                # Log the removal in streaming_change_log
                # Record removed platform in history
                cursor.execute("""
                    INSERT INTO streaming_change_log
                    (
                        letterboxd_slug,
                        country_code,
                        platform_name,
                        availability_type,
                        change_type
                    )
                    VALUES (%s, %s, %s, %s, %s);
                """, (
                    movie_slug,
                    country_code,
                    platform,
                    availability,
                    "removed"
                ))
            # Refresh unchanged records
            cursor.execute("""
                UPDATE movie_streaming
                SET last_checked = NOW()
                WHERE letterboxd_slug = %s
                  AND country_code = %s;
            """, (movie_slug, country_code))

            print("Added:", added)
            print("Removed:", removed)

            return added, removed

    
if __name__ == "__main__":
    check_streaming_changes(
        "interstellar",
        "US",
        [
            ("Apple TV", "rent"),
            ("paramount+", "subscription"),
            ("Netflix", "subscription")
        ]
    )
