from __future__ import annotations

from rq import Connection, Worker

from backend.queue import QUEUE_NAME, get_redis


def main() -> None:
    redis_conn = get_redis()
    with Connection(redis_conn):
        worker = Worker([QUEUE_NAME])
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()

