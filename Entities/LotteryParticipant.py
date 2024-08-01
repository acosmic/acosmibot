class LotteryParticipant:
    def __init__(self, event_id, participant_id) -> None:
        self.event_id = event_id
        self.participant_id = participant_id

    @property
    def event_id(self):
        return self._event_id
    
    @event_id.setter
    def event_id(self, value):
        self._event_id = value
    
    @property
    def participant_id(self):
        return self._participant_id
    
    @participant_id.setter
    def participant_id(self, value):
        self._participant_id = value