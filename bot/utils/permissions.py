"""
Permission checking utilities for Discord members.
"""

from typing import Optional

import discord

from bot.config import get_settings


def is_staff(member: discord.Member) -> bool:
    """
    Check if a member has staff permissions.
    
    Args:
        member: Discord member to check
        
    Returns:
        True if member is staff
    """
    settings = get_settings()
    
    # Check for administrator or manage guild permissions
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    
    # Check for support role
    role_ids = {r.id for r in member.roles}
    support_id = settings.support_role_id if hasattr(settings, 'support_role_id') else None
    admin_id = settings.admin_role_id if hasattr(settings, 'admin_role_id') else None
    
    if support_id and int(support_id) in role_ids:
        return True
    if admin_id and int(admin_id) in role_ids:
        return True
    
    return False


def is_admin(member: discord.Member) -> bool:
    """
    Check if a member has admin permissions.
    
    Args:
        member: Discord member to check
        
    Returns:
        True if member is admin
    """
    settings = get_settings()
    
    # Check for administrator permission
    if member.guild_permissions.administrator:
        return True
    
    # Check for admin role
    role_ids = {r.id for r in member.roles}
    admin_id = settings.admin_role_id if hasattr(settings, 'admin_role_id') else None
    
    if admin_id and int(admin_id) in role_ids:
        return True
    
    return False


def has_permission(member: discord.Member, permission: discord.Permissions) -> bool:
    """
    Check if a member has a specific permission.
    
    Args:
        member: Discord member to check
        permission: Permission to check for
        
    Returns:
        True if member has the permission
    """
    return member.guild_permissions >= permission


def can_manage_ticket(member: discord.Member, ticket_owner_id: int) -> bool:
    """
    Check if a member can manage a specific ticket.
    
    Args:
        member: Discord member to check
        ticket_owner_id: ID of the ticket owner
        
    Returns:
        True if member can manage the ticket
    """
    # Staff can always manage tickets
    if is_staff(member):
        return True
    
    # Ticket owner can manage their own ticket
    if member.id == ticket_owner_id:
        return True
    
    return False


def can_close_ticket(member: discord.Member, ticket_owner_id: int) -> bool:
    """
    Check if a member can close a specific ticket.
    
    Args:
        member: Discord member to check
        ticket_owner_id: ID of the ticket owner
        
    Returns:
        True if member can close the ticket
    """
    # Staff can always close tickets
    if is_staff(member):
        return True
    
    # Ticket owner can close their own ticket
    if member.id == ticket_owner_id:
        return True
    
    return False
