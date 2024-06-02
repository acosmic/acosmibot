class SlotEvent:
    def __init__(self, id, discord_id, slot1, slot2, slot3, amount_won, amount_lost, timestamp) -> None:
        self.id = id
        self.discord_id = discord_id
        self.slot1 = slot1
        self.slot2 = slot2
        self.slot3 = slot3
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
    def slot1(self):
        return self._slot1

    @slot1.setter
    def slot1(self, value):
        self._slot1 = value

    @property
    def slot2(self):
        return self._slot2

    @slot2.setter
    def slot2(self, value):
        self._slot2 = value

    @property
    def slot3(self):
        return self._slot3

    @slot3.setter
    def slot3(self, value):
        self._slot3 = value

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