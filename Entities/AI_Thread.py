class AI_Thread:
    def __init__(self, id, discord_id, thread_id, timestamp) -> None:
        self.id = id
        self.discord_id = discord_id
        self.thread_id = thread_id
        self.timestamp = timestamp
        
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, value):
        self._id = value

    @property
    def discord_id(self):
        return self._discord_id
    
    @discord_id.setter
    def discord_id(self, value):
        self._discord_id = value

    @property
    def thread_id(self):
        return self._thread_id
    
    @thread_id.setter
    def thread_id(self, value):
        self._thread_id = value

    @property
    def timestamp(self):
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value