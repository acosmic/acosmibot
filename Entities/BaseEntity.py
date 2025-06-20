from typing import Any, Dict, TypeVar, Generic, Optional
from datetime import datetime

T = TypeVar('T')

class BaseEntity:
    """
    Base class for all entity models.
    Provides common functionality for all entities.
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entity to a dictionary.
        Useful for serialization and data transfer.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the entity
        """
        return {key.lstrip('_'): value for key, value in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEntity':
        """
        Create an entity from a dictionary.
        Useful for deserialization.
        
        Args:
            data (Dict[str, Any]): Dictionary with entity data
            
        Returns:
            BaseEntity: New entity instance
        """
        instance = cls.__new__(cls)
        for key, value in data.items():
            setattr(instance, f"_{key}", value)
        return instance
    
    def __str__(self) -> str:
        """
        String representation of the entity.
        
        Returns:
            str: String representation
        """
        attributes = ', '.join(f"{key.lstrip('_')}={value}" for key, value in self.__dict__.items())
        return f"{self.__class__.__name__}({attributes})"