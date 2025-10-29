#! /usr/bin/python3.10
"""
AuditLog Entity
Represents an audit log entry for admin actions
"""

from typing import Optional, Dict, Any
from datetime import datetime
from Entities.BaseEntity import BaseEntity


class AuditLog(BaseEntity):
    """Entity representing an audit log entry"""

    def __init__(
        self,
        id: Optional[int] = None,
        admin_id: Optional[str] = None,
        admin_username: Optional[str] = None,
        action_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        """
        Initialize AuditLog entity

        Args:
            id: Log entry ID (primary key)
            admin_id: Discord ID of admin who performed action
            admin_username: Username of admin
            action_type: Type of action performed
            target_type: Type of entity affected
            target_id: ID of affected entity
            changes: Dictionary of changes made
            ip_address: IP address of admin
            created_at: When the action was logged
        """
        self._id = id
        self._admin_id = admin_id
        self._admin_username = admin_username
        self._action_type = action_type
        self._target_type = target_type
        self._target_id = target_id
        self._changes = changes
        self._ip_address = ip_address
        self._created_at = created_at

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def admin_id(self) -> Optional[str]:
        return self._admin_id

    @property
    def admin_username(self) -> Optional[str]:
        return self._admin_username

    @property
    def action_type(self) -> Optional[str]:
        return self._action_type

    @property
    def target_type(self) -> Optional[str]:
        return self._target_type

    @property
    def target_id(self) -> Optional[str]:
        return self._target_id

    @property
    def changes(self) -> Optional[Dict[str, Any]]:
        return self._changes

    @property
    def ip_address(self) -> Optional[str]:
        return self._ip_address

    @property
    def created_at(self) -> Optional[datetime]:
        return self._created_at
