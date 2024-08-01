class DeathrollEvent:
    def __init__(self, id, initiator, acceptor, bet, message_id, current_roll, current_player, is_finished) -> None:
        self.id = id
        self.initiator = initiator
        self.acceptor = acceptor
        self.bet = bet
        self.message_id = message_id
        self.current_roll = current_roll
        self.current_player = current_player
        self.is_finished = is_finished

    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, value):
        self._id = value

    @property
    def initiator(self):
        return self._initiator
    
    @initiator.setter
    def initiator(self, value):
        self._initiator = value

    @property
    def acceptor(self):
        return self._acceptor
    
    @acceptor.setter
    def acceptor(self, value):
        self._acceptor = value

    @property
    def bet(self):
        return self._bet
    
    @bet.setter
    def bet(self, value):
        self._bet = value

    @property
    def message_id(self):
        return self._message_id

    @message_id.setter
    def message_id(self, value):
        self._message_id = value

    @property
    def current_roll(self):
        return self._current_roll
    
    @current_roll.setter
    def current_roll(self, value):
        self._current_roll = value

    @property
    def current_player(self):
        return self._current_player
    
    @current_player.setter
    def current_player(self, value):
        self._current_player = value

    @property
    def is_finished(self):
        return self._is_finished
    
    @is_finished.setter
    def is_finished(self, value):
        self._is_finished = value

    