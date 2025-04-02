from typing import Optional, List
from database import Database
from Dao.BaseDao import BaseDao
from Entities.Invite import Invite
import logging

class InviteDao(BaseDao[Invite]):
    """
    Data Access Object for Invite entities.
    Provides methods to interact with the Invite table in the database.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the InviteDao with connection parameters.
        
        Args:
            db (Optional[Database], optional): Database connection. Defaults to None.
        """
        super().__init__(Invite, "Invite", db)
        
    def create_table(self) -> bool:
        """
        Create the Invite table if it doesn't exist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS Invite (
                id INT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                inviter_id BIGINT NOT NULL,
                invitee_id BIGINT NOT NULL,
                code VARCHAR(255) NOT NULL,
                timestamp DATETIME NOT NULL,
                UNIQUE KEY (guild_id, inviter_id, invitee_id)
            )
        """
        
        try:
            self.create_table_if_not_exists(create_table_sql)
            return True
        except Exception as e:
            self.logger.error(f"Error creating Invite table: {e}")
            return False
    
    def add_new_invite(self, invite: Invite) -> bool:
        """
        Add a new invite to the database.
        
        Args:
            invite (Invite): Invite to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            INSERT INTO Invite (id, guild_id, inviter_id, invitee_id, code, timestamp) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            invite.id,
            invite.guild_id,
            invite.inviter_id,
            invite.invitee_id,
            invite.code,
            invite.timestamp
        )
        
        try:
            self.execute_query(sql, values, commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error adding invite: {e}")
            return False

    def get_invites(self, guild_id: int) -> List[Invite]:
        """
        Get all invites for a specific guild.
        
        Args:
            guild_id (int): Discord guild ID
            
        Returns:
            List[Invite]: List of invites
        """
        sql = """
            SELECT id, guild_id, inviter_id, invitee_id, code, timestamp
            FROM Invite
            WHERE guild_id = %s
        """
        
        try:
            results = self.execute_query(sql, (guild_id,))
            
            invites = []
            if results:
                for invite_data in results:
                    invites.append(Invite(
                        invite_data[0], invite_data[1], invite_data[2], 
                        invite_data[3], invite_data[4], invite_data[5]
                    ))
            
            return invites
            
        except Exception as e:
            self.logger.error(f"Error getting invites: {e}")
            return []
    
    def get_invite(self, code: str) -> Optional[Invite]:
        """
        Get an invite by its code.
        
        Args:
            code (str): Discord invite code
            
        Returns:
            Optional[Invite]: Invite if found, None otherwise
        """
        sql = """
            SELECT id, guild_id, inviter_id, invitee_id, code, timestamp
            FROM Invite
            WHERE code = %s
        """
        
        try:
            result = self.execute_query(sql, (code,))
            
            if result and len(result) > 0:
                invite_data = result[0]
                return Invite(
                    invite_data[0], invite_data[1], invite_data[2], 
                    invite_data[3], invite_data[4], invite_data[5]
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting invite: {e}")
            return None
    
    def get_inviter(self, code: str) -> Optional[int]:
        """
        Get the inviter ID for a specific invite code.
        
        Args:
            code (str): Discord invite code
            
        Returns:
            Optional[int]: Inviter ID if found, None otherwise
        """
        sql = """
            SELECT inviter_id
            FROM Invite
            WHERE code = %s
        """
        
        try:
            result = self.execute_query(sql, (code,))
            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            self.logger.error(f"Error getting inviter: {e}")
            return None
    
    def get_invitee(self, code: str) -> Optional[int]:
        """
        Get the invitee ID for a specific invite code.
        
        Args:
            code (str): Discord invite code
            
        Returns:
            Optional[int]: Invitee ID if found, None otherwise
        """
        sql = """
            SELECT invitee_id
            FROM Invite
            WHERE code = %s
        """
        
        try:
            result = self.execute_query(sql, (code,))
            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            self.logger.error(f"Error getting invitee: {e}")
            return None
    
    def get_invites_by_inviter(self, inviter_id: int) -> List[Invite]:
        """
        Get all invites created by a specific inviter.
        
        Args:
            inviter_id (int): Discord user ID of the inviter
            
        Returns:
            List[Invite]: List of invites
        """
        sql = """
            SELECT id, guild_id, inviter_id, invitee_id, code, timestamp
            FROM Invite
            WHERE inviter_id = %s
        """
        
        try:
            results = self.execute_query(sql, (inviter_id,))
            
            invites = []
            if results:
                for invite_data in results:
                    invites.append(Invite(
                        invite_data[0], invite_data[1], invite_data[2], 
                        invite_data[3], invite_data[4], invite_data[5]
                    ))
            
            return invites
            
        except Exception as e:
            self.logger.error(f"Error getting invites by inviter: {e}")
            return []
    
    def count_invites_by_inviter(self, inviter_id: int) -> int:
        """
        Count the number of invites created by a specific inviter.
        
        Args:
            inviter_id (int): Discord user ID of the inviter
            
        Returns:
            int: Number of invites
        """
        sql = """
            SELECT COUNT(*)
            FROM Invite
            WHERE inviter_id = %s
        """
        
        try:
            result = self.execute_query(sql, (inviter_id,))
            return result[0][0] if result and result[0][0] else 0
        except Exception as e:
            self.logger.error(f"Error counting invites by inviter: {e}")
            return 0
    
    def delete_invite(self, code: str) -> bool:
        """
        Delete an invite by its code.
        
        Args:
            code (str): Discord invite code
            
        Returns:
            bool: True if successful, False otherwise
        """
        sql = """
            DELETE FROM Invite
            WHERE code = %s
        """
        
        try:
            self.execute_query(sql, (code,), commit=True)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting invite: {e}")
            return False
    
    def save(self, invite: Invite) -> Optional[Invite]:
        """
        Save an invite to the database (insert if new, update if exists).
        
        Args:
            invite (Invite): Invite to save
            
        Returns:
            Optional[Invite]: Saved invite or None on error
        """
        try:
            # For invites, we usually just insert new ones
            if self.add_new_invite(invite):
                return invite
            return None
        except Exception as e:
            self.logger.error(f"Error saving invite: {e}")
            return None