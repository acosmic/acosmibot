class LotteryEvent:
    def __init__(self, id, message_id, start_time, end_time, credits, winner_id) -> None:
        self.id = id
        self.message_id = message_id
        self.start_time = start_time
        self.end_time = end_time
        self.credits = credits
        self.winner_id = winner_id

    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, value):
        self._id = value

    @property
    def message_id(self):
        return self._message_id
    
    @message_id.setter
    def message_id(self, value):
        self._message_id = value

    @property
    def start_time(self):
        return self._start_time
    
    @start_time.setter
    def start_time(self, value):
        self._start_time = value

    @property
    def end_time(self):
        return self._end_time
    
    @end_time.setter
    def end_time(self, value):
        self._end_time = value

    @property
    def credits(self):
        return self._credits
    
    @credits.setter
    def credits(self, value):
        self._credits = value

    @property
    def winner_id(self):
        return self._winner_id
    
    @winner_id.setter
    def winner_id(self, value):
        self._winner_id = value


    