import redis
from rq import Worker, Queue
from config import REDIS_URL, THROTTLE_MAX_WAIT
from db.session import init_db
from pipeline.http import set_throttle
from pipeline.throttle import build_from_config


def setup_throttle(conn):
    set_throttle(build_from_config(conn), max_wait=THROTTLE_MAX_WAIT)


def main():
    init_db()
    conn = redis.Redis.from_url(REDIS_URL)
    setup_throttle(conn)
    Worker([Queue("wf", connection=conn)], connection=conn).work()


if __name__ == "__main__":
    main()
