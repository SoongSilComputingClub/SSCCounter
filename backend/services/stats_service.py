from decimal import Decimal

from database import get_db_connection


def to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return value


def get_current_status_from_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    current_people_count,
                    updated_at,
                    today_max_people_count,
                    today_avg_people_count
                FROM dashboard.current_status
                WHERE id = 1
                  AND updated_at >= date_trunc('day', now())
                  AND updated_at < date_trunc('day', now()) + interval '1 day'
                """
            )
            row = cur.fetchone()

    if row is None:
        return {
            "count": 0,
            "updated_at": None,
            "today_max_count": 0,
            "today_avg_count": 0.0,
        }

    return {
        "count": row[0],
        "updated_at": row[1].isoformat() if row[1] else None,
        "today_max_count": row[2],
        "today_avg_count": to_float(row[3]),
    }


def save_failed_inference(
    error_message: str,
    trigger_type: str = "scheduled",
    inference_time_ms: int | None = None,
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin.capture_logs (
                    people_count,
                    status,
                    trigger_type,
                    inference_time_ms,
                    error_message
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (None, "failed", trigger_type, inference_time_ms, error_message),
            )


def save_successful_inference(
    people_count: int,
    trigger_type: str = "scheduled",
    inference_time_ms: int | None = None,
):
    """
    YOLO 추론 성공 결과를 admin raw log와 dashboard summary tables에 반영합니다.

    처리 순서:
    1. admin.capture_logs insert
    2. dashboard.current_status update
    3. dashboard.today_hourly_stats update
    4. dashboard.daily_stats update
    5. dashboard.weekday_hourly_stats update
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin.capture_logs (
                    people_count,
                    status,
                    trigger_type,
                    inference_time_ms
                )
                VALUES (%s, %s, %s, %s)
                RETURNING measured_at
                """,
                (people_count, "success", trigger_type, inference_time_ms),
            )
            measured_at = cur.fetchone()[0]

            cur.execute(
                """
                WITH today_summary AS (
                    SELECT
                        COALESCE(MAX(people_count), 0) AS today_max_people_count,
                        COALESCE(
                            ROUND(AVG(people_count)::numeric, 2),
                            0
                        ) AS today_avg_people_count
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= date_trunc('day', now())
                      AND measured_at < date_trunc('day', now()) + interval '1 day'
                )
                INSERT INTO dashboard.current_status (
                    id,
                    current_people_count,
                    updated_at,
                    today_max_people_count,
                    today_avg_people_count
                )
                SELECT
                    1,
                    %s,
                    %s,
                    today_max_people_count,
                    today_avg_people_count
                FROM today_summary
                ON CONFLICT (id)
                DO UPDATE SET
                    current_people_count = EXCLUDED.current_people_count,
                    updated_at = EXCLUDED.updated_at,
                    today_max_people_count = EXCLUDED.today_max_people_count,
                    today_avg_people_count = EXCLUDED.today_avg_people_count
                """,
                (people_count, measured_at),
            )

            cur.execute(
                """
                WITH hourly AS (
                    SELECT
                        current_date AS stat_date,
                        EXTRACT(HOUR FROM measured_at)::int AS hour,
                        ROUND(AVG(people_count)::numeric, 2) AS avg_people_count,
                        MAX(people_count) AS max_people_count,
                        COUNT(*) AS sample_count
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= date_trunc('day', now())
                      AND measured_at < date_trunc('day', now()) + interval '1 day'
                    GROUP BY stat_date, hour
                )
                INSERT INTO dashboard.today_hourly_stats (
                    stat_date,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    updated_at
                )
                SELECT
                    stat_date,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    now()
                FROM hourly
                ON CONFLICT (stat_date, hour)
                DO UPDATE SET
                    avg_people_count = EXCLUDED.avg_people_count,
                    max_people_count = EXCLUDED.max_people_count,
                    sample_count = EXCLUDED.sample_count,
                    updated_at = EXCLUDED.updated_at
                """
            )

            cur.execute(
                """
                WITH base AS (
                    SELECT
                        people_count,
                        measured_at,
                        EXTRACT(HOUR FROM measured_at)::int AS hour
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= date_trunc('day', now())
                      AND measured_at < date_trunc('day', now()) + interval '1 day'
                ),
                hourly AS (
                    SELECT
                        hour,
                        ROUND(AVG(people_count)::numeric, 2) AS avg_people_count
                    FROM base
                    WHERE hour BETWEEN 9 AND 22
                    GROUP BY hour
                ),
                summary AS (
                    SELECT
                        current_date AS stat_date,
                        COALESCE(
                            ROUND(AVG(people_count)::numeric, 2),
                            0
                        ) AS avg_people_count,
                        COALESCE(MAX(people_count), 0) AS max_people_count,
                        COALESCE(MIN(people_count), 0) AS min_people_count,
                        COUNT(*) AS sample_count
                    FROM base
                ),
                peak AS (
                    SELECT hour AS peak_hour
                    FROM hourly
                    ORDER BY avg_people_count DESC, hour ASC
                    LIMIT 1
                ),
                quiet AS (
                    SELECT hour AS quiet_hour
                    FROM hourly
                    ORDER BY avg_people_count ASC, hour ASC
                    LIMIT 1
                )
                INSERT INTO dashboard.daily_stats (
                    stat_date,
                    avg_people_count,
                    max_people_count,
                    min_people_count,
                    peak_hour,
                    quiet_hour,
                    sample_count,
                    updated_at
                )
                SELECT
                    summary.stat_date,
                    summary.avg_people_count,
                    summary.max_people_count,
                    summary.min_people_count,
                    peak.peak_hour,
                    quiet.quiet_hour,
                    summary.sample_count,
                    now()
                FROM summary
                LEFT JOIN peak ON true
                LEFT JOIN quiet ON true
                ON CONFLICT (stat_date)
                DO UPDATE SET
                    avg_people_count = EXCLUDED.avg_people_count,
                    max_people_count = EXCLUDED.max_people_count,
                    min_people_count = EXCLUDED.min_people_count,
                    peak_hour = EXCLUDED.peak_hour,
                    quiet_hour = EXCLUDED.quiet_hour,
                    sample_count = EXCLUDED.sample_count,
                    updated_at = EXCLUDED.updated_at
                """
            )

            cur.execute(
                """
                WITH weekday_hourly AS (
                    SELECT
                        EXTRACT(ISODOW FROM measured_at)::int AS weekday,
                        EXTRACT(HOUR FROM measured_at)::int AS hour,
                        ROUND(AVG(people_count)::numeric, 2) AS avg_people_count,
                        MAX(people_count) AS max_people_count,
                        COUNT(*) AS sample_count
                    FROM admin.capture_logs
                    WHERE status = 'success'
                      AND measured_at >= now() - interval '4 weeks'
                      AND EXTRACT(ISODOW FROM measured_at)::int BETWEEN 1 AND 5
                      AND EXTRACT(HOUR FROM measured_at)::int BETWEEN 9 AND 22
                    GROUP BY weekday, hour
                )
                INSERT INTO dashboard.weekday_hourly_stats (
                    weekday,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    updated_at
                )
                SELECT
                    weekday,
                    hour,
                    avg_people_count,
                    max_people_count,
                    sample_count,
                    now()
                FROM weekday_hourly
                ON CONFLICT (weekday, hour)
                DO UPDATE SET
                    avg_people_count = EXCLUDED.avg_people_count,
                    max_people_count = EXCLUDED.max_people_count,
                    sample_count = EXCLUDED.sample_count,
                    updated_at = EXCLUDED.updated_at
                """
            )


def get_today_stats_from_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT hours.hour, COALESCE(stats.avg_people_count, 0) AS count
                FROM generate_series(9, 22) AS hours(hour)
                LEFT JOIN dashboard.today_hourly_stats AS stats
                  ON stats.hour = hours.hour
                 AND stats.stat_date = current_date
                ORDER BY hours.hour
                """
            )
            rows = cur.fetchall()

    return [{"hour": row[0], "count": row[1]} for row in rows]


def get_weekly_stats_from_db():
    day_key_map = {
        1: "mon",
        2: "tue",
        3: "wed",
        4: "thu",
        5: "fri",
    }

    weekly_stats = {
        "mon": [0] * 14,
        "tue": [0] * 14,
        "wed": [0] * 14,
        "thu": [0] * 14,
        "fri": [0] * 14,
    }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    weekday,
                    hour,
                    avg_people_count
                FROM dashboard.weekday_hourly_stats
                WHERE weekday BETWEEN 1 AND 5
                  AND hour BETWEEN 9 AND 22
                ORDER BY weekday, hour
                """
            )
            rows = cur.fetchall()

    for weekday, hour, avg_people_count in rows:
        day_key = day_key_map.get(weekday)

        if not day_key:
            continue

        index = hour - 9

        if 0 <= index < 14:
            weekly_stats[day_key][index] = to_float(avg_people_count)

    return weekly_stats
