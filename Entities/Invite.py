class Invite:
    def __init__(self, id, guild_id, inviter_id, invitee_id, code, timestamp):
        self.id = id
        self.guild_id = guild_id
        self.inviter_id = inviter_id
        self.invitee_id = invitee_id
        self.code = code
        self.timestamp = timestamp

    def __str__(self):
        return f"Invite: {self.invitee_id} invited by {self.inviter_id} in {self.guild_id} at {self.timestamp}"
    
    @property
    def id(self):
        return self._id
    @id.setter
    def id(self, value):
        self._id = value
    

    @property
    def guild_id(self):
        return self._guild_id
    @guild_id.setter
    def guild_id(self, value):
        self._guild_id = value

    @property
    def inviter_id(self):
        return self._inviter_id
    @inviter_id.setter
    def inviter_id(self, value):
        self._inviter_id = value
    
    @property
    def invitee_id(self):
        return self._invitee_id
    @invitee_id.setter
    def invitee_id(self, value):
        self._invitee_id = value

    @property
    def code(self):
        return self._code
    @code.setter
    def code(self, value):
        self._code = value

    @property
    def timestamp(self):
        return self._timestamp
    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value

# Path: Entities/User.py
        