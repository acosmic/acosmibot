class User:
    def __init__(self, id, discord_username, level, streak, exp, exp_gained, exp_lost, messages_sent, reactions_sent, created, last_active) -> None:
        self.id = id
        self.discord_username = discord_username
        self.level = level
        self.streak = streak
        self.exp = exp
        self.exp_gained = exp_gained
        self.exp_lost = exp_lost
        self.messages_sent = messages_sent
        self.reactions_sent = reactions_sent
        self.created = created
        self.last_active = last_active

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        # Add validation logic if needed
        self._level = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        # Add validation logic if needed
        self._id = value

    @property
    def discord_username(self):
        return self._discord_username

    @discord_username.setter
    def discord_username(self, value):
        # Add validation logic if needed
        self._discord_username = value

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        # Add validation logic if needed
        self._level = value

    @property
    def streak(self):
        return self._streak

    @streak.setter
    def streak(self, value):
        # Add validation logic if needed
        self._streak = value

    @property
    def exp(self):
        return self._exp

    @exp.setter
    def exp(self, value):
        # Add validation logic if needed
        self._exp = value

    @property
    def exp_gained(self):
        return self._exp_gained

    @exp_gained.setter
    def exp_gained(self, value):
        # Add validation logic if needed
        self._exp_gained = value

    @property
    def exp_lost(self):
        return self._exp_lost

    @exp_lost.setter
    def exp_lost(self, value):
        # Add validation logic if needed
        self._exp_lost = value

    @property
    def messages_sent(self):
        return self._messages_sent

    @messages_sent.setter
    def messages_sent(self, value):
        # Add validation logic if needed
        self._messages_sent = value

    @property
    def reactions_sent(self):
        return self._reactions_sent

    @reactions_sent.setter
    def reactions_sent(self, value):
        # Add validation logic if needed
        self._reactions_sent = value

    @property
    def created(self):
        return self._created

    @created.setter
    def created(self, value):
        # Add validation logic if needed
        self._created = value

    @property
    def last_active(self):
        return self._last_active

    @last_active.setter
    def last_active(self, value):
        # Add validation logic if needed
        self._last_active = value
