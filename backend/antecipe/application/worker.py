import time
from antecipe.ports.worker import WorkerRepository


def serve(repository: WorkerRepository, once=False):
    while True:
        worked = repository.run_once()
        if once:
            return worked
        if not worked:
            time.sleep(1)
