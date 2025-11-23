import heapq
import itertools

class UserPriorityQueue:
    """
    Min-heap based on priority.
    Uses a tiebreaker counter so dicts are never compared.
    """

    def __init__(self):
        self.heap = []
        self.counter = itertools.count()   # unique increasing counter

    def push(self, priority, user):
        # (priority, counter, user)
        heapq.heappush(self.heap, (priority, next(self.counter), user))

    def pop(self):
        if self.heap:
            return heapq.heappop(self.heap)[2]  # return user
        return None

    def __len__(self):
        return len(self.heap)

    def clear(self):
        self.heap = []
        self.counter = itertools.count()
