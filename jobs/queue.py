import redis
from rq import Queue
from config import REDIS_URL


def get_queue(conn=None) -> Queue:
    conn = conn or redis.Redis.from_url(REDIS_URL)
    return Queue("wf", connection=conn)


def enqueue_job(job_id: str, conn=None):
    return get_queue(conn).enqueue("worker.process.process_job", job_id)
