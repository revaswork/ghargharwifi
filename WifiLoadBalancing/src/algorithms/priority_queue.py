import heapq
import itertools

class UserPriorityQueue:
    """
    Stable min-heap priority queue for users.
    
    - Supports multi-component priorities (tuple priority)
    - Lower priority value gets popped first
    - Counter ensures stability and no dict comparison
    """

    def __init__(self):
        self.heap = []
        self.counter = itertools.count()

    def push(self, priority, user):
        """
        Push a user with priority.

        priority can be:
            • int/float   (simple)
            • tuple       (multi-factor priority)
        """
        entry = (priority, next(self.counter), user)
        heapq.heappush(self.heap, entry)

    def pop(self):
        """Return user with smallest priority score."""
        if not self.heap:
            return None
        return heapq.heappop(self.heap)[2]

    def __len__(self):
        return len(self.heap)

    def clear(self):
        self.heap = []
        self.counter = itertools.count()
