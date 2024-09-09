class AI_Thread:
    def __init__(self, discord_id, thread_id, temperature, timestamp) -> None:
        self.discord_id = discord_id
        self.thread_id = thread_id
        self.temperature = temperature
        self.timestamp = timestamp

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
    def temperature(self):
        return self._temperature
    
    @temperature.setter
    def temperature(self, value):
        self._temperature = value

    @property
    def timestamp(self):
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value