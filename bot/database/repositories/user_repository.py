"""
User repository for database operations.
"""

import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Repository for user-related database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by Discord ID."""
        return await self.session.get(User, user_id)
    
    async def create_user(
        self,
        user_id: int,
        username: str,
        discriminator: str,
        global_name: Optional[str] = None,
        avatar: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        now = datetime.datetime.now(datetime.timezone.utc)
        user = User(
            id=user_id,
            username=username,
            discriminator=discriminator,
            global_name=global_name,
            avatar=avatar,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        
        logger.info(f"Created user {user_id} ({username})")
        return user
    
    async def get_or_create_user(
        self,
        user_id: int,
        username: str,
        discriminator: str,
        global_name: Optional[str] = None,
        avatar: Optional[str] = None,
    ) -> User:
        """Get existing user or create new one."""
        user = await self.get_user(user_id)
        
        if user is None:
            user = await self.create_user(user_id, username, discriminator, global_name, avatar)
        else:
            # Update user info if changed
            user.username = username
            user.discriminator = discriminator
            user.global_name = global_name
            user.avatar = avatar
            user.last_seen_at = datetime.datetime.now(datetime.timezone.utc)
            user.updated_at = datetime.datetime.now(datetime.timezone.utc)
            await self.session.flush()
        
        return user
    
    async def update_user(self, user: User) -> User:
        """Update a user."""
        user.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await self.session.flush()
        await self.session.refresh(user)
        return user
    
    async def set_staff_status(self, user: User, is_staff: bool) -> User:
        """Set staff status for a user."""
        user.is_staff = is_staff
        user.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await self.session.flush()
        await self.session.refresh(user)
        
        logger.info(f"User {user.id} staff status set to {is_staff}")
        return user
    
    async def set_staff_specialization(self, user: User, specialization: str) -> User:
        """Set staff specialization for a user."""
        user.staff_specialization = specialization
        user.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await self.session.flush()
        await self.session.refresh(user)
        
        logger.info(f"User {user.id} specialization set to {specialization}")
        return user
    
    async def set_language_preference(self, user: User, language: str) -> User:
        """Set language preference for a user."""
        user.language = language
        user.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await self.session.flush()
        await self.session.refresh(user)
        
        logger.info(f"User {user.id} language preference set to {language}")
        return user
    
    async def increment_tickets_created(self, user: User) -> User:
        """Increment tickets created counter."""
        user.increment_tickets_created()
        await self.session.flush()
        return user
    
    async def increment_tickets_closed(self, user: User) -> User:
        """Increment tickets closed counter."""
        user.increment_tickets_closed()
        await self.session.flush()
        return user
    
    async def increment_tickets_claimed(self, user: User) -> User:
        """Increment tickets claimed counter (staff only)."""
        user.increment_tickets_claimed()
        await self.session.flush()
        return user
    
    async def increment_tickets_resolved(self, user: User) -> User:
        """Increment tickets resolved counter (staff only)."""
        user.increment_tickets_resolved()
        await self.session.flush()
        return user
    
    async def update_response_time(self, user: User, response_seconds: int) -> User:
        """Update response time statistics (staff only)."""
        user.update_response_time(response_seconds)
        await self.session.flush()
        return user
    
    async def get_staff_members(self, guild_id: int) -> List[User]:
        """Get all staff members (placeholder - would need guild-specific filtering)."""
        # In a real implementation, this would filter by guild membership
        query = select(User).where(User.is_staff == True)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_staff_by_specialization(self, specialization: str) -> List[User]:
        """Get staff members by specialization."""
        query = select(User).where(
            and_(User.is_staff == True, User.staff_specialization == specialization)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_top_staff_by_resolved(self, limit: int = 10) -> List[User]:
        """Get top staff members by tickets resolved."""
        query = (
            select(User)
            .where(User.is_staff == True)
            .order_by(User.tickets_resolved.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_staff_with_least_active_tickets(self, guild_id: int) -> Optional[User]:
        """Get staff member with the least active tickets (for auto-assignment)."""
        # This would be a more complex query in a real implementation
        # involving joins with the tickets table
        query = (
            select(User)
            .where(User.is_staff == True)
            .order_by(User.tickets_claimed.asc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
