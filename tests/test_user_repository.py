"""
Tests for user repository.
"""

import pytest

from bot.database.connection import get_session
from bot.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_user():
    """Test creating a new user."""
    async with get_session() as session:
        repo = UserRepository(session)
        
        user = await repo.create_user(
            user_id=123456789,
            username="testuser",
            discriminator="1234",
            global_name="Test User",
        )
        
        assert user.id == 123456789
        assert user.username == "testuser"
        assert user.tickets_created == 0
        assert user.is_staff is False


@pytest.mark.asyncio
async def test_get_or_create_user():
    """Test getting or creating a user."""
    async with get_session() as session:
        repo = UserRepository(session)
        
        user_id = 987654321
        
        # First call should create
        user1 = await repo.get_or_create_user(
            user_id=user_id,
            username="newuser",
            discriminator="5678",
            global_name="New User",
        )
        
        assert user1.id == user_id
        assert user1.username == "newuser"
        
        # Second call should retrieve existing
        user2 = await repo.get_or_create_user(
            user_id=user_id,
            username="newuser",
            discriminator="5678",
            global_name="New User",
        )
        
        assert user2.id == user_id
        assert user1.id == user2.id


@pytest.mark.asyncio
async def test_set_staff_status():
    """Test setting staff status."""
    async with get_session() as session:
        repo = UserRepository(session)
        
        user = await repo.create_user(
            user_id=111222333,
            username="staffuser",
            discriminator="9999",
        )
        
        # Set as staff
        staff_user = await repo.set_staff_status(user, is_staff=True)
        
        assert staff_user.is_staff is True


@pytest.mark.asyncio
async def test_increment_tickets_created():
    """Test incrementing tickets created counter."""
    async with get_session() as session:
        repo = UserRepository(session)
        
        user = await repo.create_user(
            user_id=444555666,
            username="ticketuser",
            discriminator="0000",
        )
        
        assert user.tickets_created == 0
        
        # Increment
        updated = await repo.increment_tickets_created(user)
        
        assert updated.tickets_created == 1
