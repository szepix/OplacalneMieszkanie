import redis
from rq import Worker, Queue
from config import REDIS_URL
from db.session import init_db


def main():
    init_db()
    conn = redis.Redis.from_url(REDIS_URL)
    Worker([Queue("wf", connection=conn)], connection=conn).work()


if __name__ == "__main__":
    main()
