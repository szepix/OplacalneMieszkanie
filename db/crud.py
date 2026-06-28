import hashlib
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from db.models import Job, JobResult


def spec_hash(spec_dict: dict) -> str:
    canon = json.dumps(spec_dict, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def create_job(session, ip: str, spec_dict: dict) -> Job:
    job = Job(ip=ip, spec=spec_dict, spec_hash=spec_hash(spec_dict), status="queued")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_job(session, job_id: str) -> Job | None:
    return session.get(Job, job_id)


def set_status(session, job_id: str, status: str, **fields) -> None:
    job = session.get(Job, job_id)
    if not job:
        return
    job.status = status
    for k, v in fields.items():
        setattr(job, k, v)
    session.commit()


def add_results(session, job_id: str, rows: list[dict]) -> None:
    for rank, row in enumerate(rows, start=1):
        session.add(JobResult(job_id=job_id, rank=rank, data=row))
    session.commit()


def find_fresh_slice(session, spec_hash: str, ttl_seconds: int, exclude_id: str) -> Job | None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
    stmt = (select(Job)
            .where(Job.spec_hash == spec_hash, Job.status == "done",
                   Job.finished_at >= cutoff, Job.id != exclude_id)
            .order_by(Job.finished_at.desc())
            .limit(1))
    return session.execute(stmt).scalar_one_or_none()
