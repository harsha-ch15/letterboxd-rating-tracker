import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_weekly_streaming_report():
    with psycopg.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    ) as conn:

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COALESCE(c.title, d.title, s.letterboxd_slug)
                        AS movie_title,

                    STRING_AGG(
                        s.platform_name || ' (' || s.change_type || ')',
                        ', '
                        ORDER BY s.platform_name
                    ) FILTER (WHERE s.country_code = 'US')
                        AS us_changes,

                    STRING_AGG(
                        s.platform_name || ' (' || s.change_type || ')',
                        ', '
                        ORDER BY s.platform_name
                    ) FILTER (WHERE s.country_code = 'IN')
                        AS india_changes

                FROM streaming_change_log AS s

                LEFT JOIN current_movies AS c
                    ON s.letterboxd_slug = c.letterboxd_slug

                LEFT JOIN demoted_movies AS d
                    ON s.letterboxd_slug = d.letterboxd_slug

                WHERE s.changed_at >= NOW() - INTERVAL '7 days'

                GROUP BY s.letterboxd_slug, c.title, d.title
                ORDER BY movie_title;
            """)

            return cursor.fetchall()
def get_weekly_rating_report():
    with psycopg.connect(
        os.environ["DATABASE_URL"],
        sslmode="require"
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COALESCE(c.title, d.title, r.letterboxd_slug)
                        AS movie_title,
                    r.change_type,
                    r.previous_rating,
                    r.current_rating
                FROM movie_rating_change_log AS r
                LEFT JOIN current_movies AS c
                    ON r.letterboxd_slug = c.letterboxd_slug
                LEFT JOIN demoted_movies AS d
                    ON r.letterboxd_slug = d.letterboxd_slug
                WHERE r.changed_at >= NOW() - INTERVAL '7 days'
                ORDER BY r.changed_at, r.change_id;
            """)

            return cursor.fetchall()
        
def format_weekly_email(rating_report, streaming_report):

    message = "Weekly Letterboxd Movie Report\n\n"

    if not rating_report and not streaming_report:
        return message + "No changes this week."

    if rating_report:
        message += "MOVIE RATING CHANGES\n"
        message += "--------------------\n"

        for movie in rating_report:
            title, change_type, old_rating, new_rating = movie

            if change_type == "added":
                message += f"{title}: Newly added (Rating: {new_rating})\n"

            elif change_type == "promoted":
                message += f"{title}: Promoted ({old_rating} -> {new_rating})\n"

            elif change_type == "demoted":
                message += f"{title}: Demoted ({old_rating} -> {new_rating})\n"

        message += "\n"

    if streaming_report:
        message += "STREAMING CHANGES\n"
        message += "-----------------\n"

        for movie in streaming_report:
            title, us_changes, india_changes = movie

            message += f"Movie: {title}\n"
            message += f"US: {us_changes or 'No changes'}\n"
            message += f"India: {india_changes or 'No changes'}\n\n"

    return message

if __name__ == "__main__":

    rating_report = get_weekly_rating_report()
    streaming_report = get_weekly_streaming_report()

    email_body = format_weekly_email(
        rating_report,
        streaming_report
    )

    print(email_body)