
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def update_movie_rating(movie_slug, new_rating):
   
    with psycopg.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    ) as conn:

        with conn.cursor() as cursor:

            # Find the movie
            cursor.execute("""
                SELECT rating
                FROM current_movies
                WHERE letterboxd_slug = %s
                FOR UPDATE;
            """, (movie_slug,))

            movie = cursor.fetchone()

            if movie is not None:
                old_rating = movie[0]
                if new_rating > 4.0:

                    # Update the existing rating
                    cursor.execute("""
                        UPDATE current_movies
                        SET rating = %s,
                            last_checked = NOW()
                        WHERE letterboxd_slug = %s;
                    """, (new_rating, movie_slug))

                    print("Movie rating updated.")

                else:

                    # Move movie into demoted_movies
                    cursor.execute("""
                        INSERT INTO demoted_movies
                        (
                            letterboxd_slug,
                            title,
                            release_year,
                            language,
                            genres,
                            previous_rating,
                            current_rating
                        )
                        SELECT
                            letterboxd_slug,
                            title,
                            release_year,
                            language,
                            genres,
                            rating,
                            %s
                        FROM current_movies
                        WHERE letterboxd_slug = %s
                        ON CONFLICT (letterboxd_slug)
                        DO UPDATE SET
                            previous_rating = EXCLUDED.previous_rating,
                            current_rating = EXCLUDED.current_rating,
                            date_demoted = NOW();
                    """, (new_rating, movie_slug))

                    inserted_rows = cursor.rowcount

                    if inserted_rows == 0:
                        raise RuntimeError(
                            "Demotion failed: no row inserted."
                        )

                    # Delete only after successful insert
                    cursor.execute("""
                        DELETE FROM current_movies
                        WHERE letterboxd_slug = %s;
                    """, (movie_slug,))
                    cursor.execute("""
                        INSERT INTO movie_rating_change_log
                        (
                            letterboxd_slug,
                            change_type,
                            previous_rating,
                            current_rating
                        )
                        VALUES (%s, %s, %s, %s);
                    """, (movie_slug, "demoted", old_rating, new_rating))

                    print("Movie successfully demoted.")

                    
                
            else:
                # Check whether the movie exists in demoted_movies
                cursor.execute("""
                    SELECT current_rating
                    FROM demoted_movies
                    WHERE letterboxd_slug = %s
                    FOR UPDATE;
                """, (movie_slug,))

                demoted_movie = cursor.fetchone()

                if demoted_movie is not None:

                    if new_rating > 4.0:
                        old_rating = demoted_movie[0]
                        # Move the movie back to current_movies
                        cursor.execute("""
                            INSERT INTO current_movies
                            (
                                letterboxd_slug,
                                title,
                                release_year,
                                language,
                                genres,
                                rating
                            )
                            SELECT
                                letterboxd_slug,
                                title,
                                release_year,
                                language,
                                genres,
                                %s
                            FROM demoted_movies
                            WHERE letterboxd_slug = %s
                            ON CONFLICT (letterboxd_slug)
                            DO UPDATE SET
                                rating = EXCLUDED.rating,
                                last_checked = NOW();
                        """, (new_rating, movie_slug))

                        if cursor.rowcount == 0:
                            raise RuntimeError("Promotion failed.")

                        cursor.execute("""
                            DELETE FROM demoted_movies
                            WHERE letterboxd_slug = %s;
                        """, (movie_slug,))

                        print("Movie successfully promoted.")

                        cursor.execute("""
                            INSERT INTO movie_rating_change_log
                            (
                                letterboxd_slug,
                                change_type,
                                previous_rating,
                                current_rating
                            )
                            VALUES (%s, %s, %s, %s);
                        """, (movie_slug, "promoted", old_rating, new_rating))

                    else:
                        # Movie still has a rating of 4.0 or below
                        cursor.execute("""
                            UPDATE demoted_movies
                            SET current_rating = %s
                            WHERE letterboxd_slug = %s;
                        """, (new_rating, movie_slug))

                        print("Movie remains demoted.")

                else:
                    print("Movie not found in either table.")




def add_new_movie(slug, title, year, language, genres, rating):

    if not 4.0 < rating <= 5.0:
        print("Movie does not qualify.")
        return

    with psycopg.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    ) as conn:

        with conn.cursor() as cursor:

            # Step 1: Check demoted_movies
            cursor.execute("""
                SELECT current_rating
                FROM demoted_movies
                WHERE letterboxd_slug = %s
                FOR UPDATE;
            """, (slug,))

            demoted_movie = cursor.fetchone()

            if demoted_movie is not None:
                old_rating = demoted_movie[0]
                # Step 2: Promote the movie
                cursor.execute("""
                    INSERT INTO current_movies
                    (
                        letterboxd_slug,
                        title,
                        release_year,
                        language,
                        genres,
                        rating
                    )
                    SELECT
                        letterboxd_slug,
                        title,
                        release_year,
                        language,
                        genres,
                        %s
                    FROM demoted_movies
                    WHERE letterboxd_slug = %s
                    ON CONFLICT (letterboxd_slug)
                    DO UPDATE SET
                        rating = EXCLUDED.rating,
                        last_checked = NOW();
                """, (rating, slug))

                if cursor.rowcount == 0:
                    raise RuntimeError("Promotion failed.")

                # Step 3: Remove from demoted_movies
                cursor.execute("""
                    DELETE FROM demoted_movies
                    WHERE letterboxd_slug = %s;
                """, (slug,))
                cursor.execute("""
                    INSERT INTO movie_rating_change_log
                    (
                        letterboxd_slug,
                        change_type,
                        previous_rating,
                        current_rating
                    )
                    VALUES (%s, %s, %s, %s);
                """, (slug, "promoted", old_rating, rating))
                print("Movie successfully promoted.")

            else:

                # Step 4: Insert a new movie
                cursor.execute("""
                    INSERT INTO current_movies
                    (
                        letterboxd_slug,
                        title,
                        release_year,
                        language,
                        genres,
                        rating
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (letterboxd_slug)
                    DO NOTHING;
                """, (
                    slug, title, year,
                    language, genres, rating
                ))

                if cursor.rowcount == 1:

                    cursor.execute("""
                        INSERT INTO movie_rating_change_log
                        (
                            letterboxd_slug,
                            change_type,
                            previous_rating,
                            current_rating
                        )
                        VALUES (%s, %s, %s, %s);
                    """, (slug, "added", None, rating))

                    print("New movie successfully added.")

                else:
                    print("Movie already exists in current_movies.")


if __name__ == "__main__":
    add_new_movie(
        "rrr",
        "RRR",
        2022,
        "te",
        ["Action", "Drama"],
        4.60
    )