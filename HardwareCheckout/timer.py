import heapq
from datetime import datetime
from multiprocessing import Process, Queue
from queue import Empty

import requests


def _background_process(queue):
    heap = []
    timeout = None
    while True:
        try:
            entry = queue.get(True, timeout)
            heapq.heappush(heap, entry)
        except Empty:
            pass
        while heap and datetime.now() >= heap[0][0]:
            uri = heapq.heappop(heap)[1]
            requests.post('http://localhost:5000/{}'.format(uri))
        if heap:
            timeout = (heap[0][0] - datetime.now()).total_seconds()
            timeout = 1 if timeout < 1 else timeout
        else:
            timeout = None


class Timer:
    def __init__(self):
        self.queue = Queue()
        self.process = Process(target=_background_process, args=(self.queue,), daemon=True)
        self.process.start()

    def add_timer(self, uri, timestamp):
        self.queue.put((timestamp, uri))
