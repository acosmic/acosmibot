class CoinflipEvent:
    def __init__(self, id, discord_id, guess, result, amount_won, amount_lost, timestamp) -> None:
        self.id = id
        self.discord_id = discord_id
        self.guess = guess
        self.result = result
        self.amount_won = amount_won
        self.amount_lost = amount_lost
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
    def guess(self):
        return self._guess

    @guess.setter
    def guess(self, value):
        self._guess = value

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = value

    @property
    def amount_won(self):
        return self._amount_won

    @amount_won.setter
    def amount_won(self, value):
        self._amount_won = value

    @property
    def amount_lost(self):
        return self._amount_lost

    @amount_lost.setter
    def amount_lost(self, value):
        self._amount_lost = value

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value