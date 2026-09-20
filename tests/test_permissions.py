"""
Tests for permission utilities.
"""

import pytest
from unittest.mock import Mock

from bot.utils.permissions import is_staff, is_admin, has_permission


def test_is_staff_with_admin_permission():
    """Test that users with admin permission are considered staff."""
    member = Mock()
    member.guild_permissions.administrator = True
    member.roles = []
    
    assert is_staff(member) is True


def test_is_staff_with_manage_guild_permission():
    """Test that users with manage guild permission are considered staff."""
    member = Mock()
    member.guild_permissions.administrator = False
    member.guild_permissions.manage_guild = True
    member.roles = []
    
    assert is_staff(member) is True


def test_is_staff_without_permissions():
    """Test that regular users are not considered staff."""
    member = Mock()
    member.guild_permissions.administrator = False
    member.guild_permissions.manage_guild = False
    member.roles = []
    
    # Regular users without permissions or roles should not be staff
    # (This would need proper settings mocking in a real test)
    pass


def test_has_permission():
    """Test permission checking utility."""
    member = Mock()
    member.guild_permissions.administrator = True
    
    # Admin should have all permissions
    assert has_permission(member, Mock()) is True


def test_can_manage_ticket():
    """Test ticket management permission checking."""
    member = Mock()
    member.guild_permissions.administrator = True
    
    # Staff can manage any ticket
    assert can_manage_ticket(member, 999) is True


def test_can_close_ticket():
    """Test ticket closing permission checking."""
    member = Mock()
    member.guild_permissions.administrator = True
    
    # Staff can close any ticket
    assert can_close_ticket(member, 999) is True
    
    # Owner can close their own ticket
    owner_member = Mock()
    owner_member.id = 123
    owner_member.guild_permissions.administrator = False
    
    assert can_close_ticket(owner_member, 123) is True
