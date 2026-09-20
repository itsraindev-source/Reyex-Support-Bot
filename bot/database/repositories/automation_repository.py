"""
Automation repository for database operations.
"""

import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.automation import SLARule, CannedResponse, EscalationRule, AutomationLog
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class AutomationRepository:
    """Repository for automation-related database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # SLA Rules
    async def create_sla_rule(
        self,
        guild_id: int,
        name: str,
        priority: str,
        first_response_target: int,
        resolution_target: int,
        description: Optional[str] = None,
        ticket_type: Optional[str] = None,
        follow_up_target: Optional[int] = None,
        alert_before_breach: int = 15,
        alert_channel_id: Optional[int] = None,
        alert_role_id: Optional[int] = None,
        business_hours_only: bool = False,
        business_hours_start: Optional[str] = None,
        business_hours_end: Optional[str] = None,
        business_days: Optional[List[str]] = None,
    ) -> SLARule:
        """Create a new SLA rule."""
        now = datetime.datetime.now(datetime.timezone.utc)
        rule = SLARule(
            guild_id=guild_id,
            name=name,
            description=description,
            priority=priority,
            ticket_type=ticket_type,
            first_response_target=first_response_target,
            resolution_target=resolution_target,
            follow_up_target=follow_up_target,
            alert_before_breach=alert_before_breach,
            alert_channel_id=alert_channel_id,
            alert_role_id=alert_role_id,
            business_hours_only=business_hours_only,
            business_hours_start=business_hours_start,
            business_hours_end=business_hours_end,
            business_days=business_days,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        
        logger.info(f"Created SLA rule '{name}' for guild {guild_id}")
        return rule
    
    async def get_sla_rules_by_guild(self, guild_id: int, active_only: bool = True) -> List[SLARule]:
        """Get SLA rules for a guild."""
        query = select(SLARule).where(SLARule.guild_id == guild_id)
        
        if active_only:
            query = query.where(SLARule.is_active == True)
        
        query = query.order_by(SLARule.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_sla_rule_by_priority(self, guild_id: int, priority: str) -> Optional[SLARule]:
        """Get SLA rule for a specific priority."""
        query = select(SLARule).where(
            and_(
                SLARule.guild_id == guild_id,
                SLARule.priority == priority,
                SLARule.is_active == True
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    # Canned Responses
    async def create_canned_response(
        self,
        guild_id: int,
        name: str,
        title: str,
        content: str,
        category: str,
        created_by: int,
        tags: Optional[List[str]] = None,
        required_role_id: Optional[int] = None,
    ) -> CannedResponse:
        """Create a new canned response."""
        now = datetime.datetime.now(datetime.timezone.utc)
        response = CannedResponse(
            guild_id=guild_id,
            name=name,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            required_role_id=required_role_id,
            is_active=True,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(response)
        await self.session.flush()
        await self.session.refresh(response)
        
        logger.info(f"Created canned response '{name}' for guild {guild_id}")
        return response
    
    async def get_canned_responses_by_guild(
        self,
        guild_id: int,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> List[CannedResponse]:
        """Get canned responses for a guild."""
        query = select(CannedResponse).where(CannedResponse.guild_id == guild_id)
        
        if category:
            query = query.where(CannedResponse.category == category)
        if active_only:
            query = query.where(CannedResponse.is_active == True)
        
        query = query.order_by(CannedResponse.usage_count.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_canned_response_by_name(self, guild_id: int, name: str) -> Optional[CannedResponse]:
        """Get a canned response by name."""
        query = select(CannedResponse).where(
            and_(
                CannedResponse.guild_id == guild_id,
                CannedResponse.name == name,
                CannedResponse.is_active == True
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def increment_canned_response_usage(self, response: CannedResponse) -> CannedResponse:
        """Increment usage counter for a canned response."""
        response.increment_usage()
        await self.session.flush()
        return response
    
    # Escalation Rules
    async def create_escalation_rule(
        self,
        guild_id: int,
        name: str,
        condition_type: str,
        condition_value: dict,
        actions: List[dict],
        description: Optional[str] = None,
        priority_filter: Optional[List[str]] = None,
        escalation_level: int = 1,
        max_escalations: int = 3,
        cooldown_minutes: int = 60,
    ) -> EscalationRule:
        """Create a new escalation rule."""
        now = datetime.datetime.now(datetime.timezone.utc)
        rule = EscalationRule(
            guild_id=guild_id,
            name=name,
            description=description,
            condition_type=condition_type,
            condition_value=condition_value,
            priority_filter=priority_filter,
            actions=actions,
            escalation_level=escalation_level,
            max_escalations=max_escalations,
            cooldown_minutes=cooldown_minutes,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        
        logger.info(f"Created escalation rule '{name}' for guild {guild_id}")
        return rule
    
    async def get_escalation_rules_by_guild(self, guild_id: int, active_only: bool = True) -> List[EscalationRule]:
        """Get escalation rules for a guild."""
        query = select(EscalationRule).where(EscalationRule.guild_id == guild_id)
        
        if active_only:
            query = query.where(EscalationRule.is_active == True)
        
        query = query.order_by(EscalationRule.escalation_level.asc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    # Automation Logs
    async def log_automation(
        self,
        guild_id: int,
        action_type: str,
        details: dict,
        triggered_by: str,
        ticket_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        rule_name: Optional[str] = None,
        triggered_by_id: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AutomationLog:
        """Log an automation action."""
        log = AutomationLog(
            guild_id=guild_id,
            ticket_id=ticket_id,
            action_type=action_type,
            rule_id=rule_id,
            rule_name=rule_name,
            details=details,
            success=success,
            error_message=error_message,
            triggered_by=triggered_by,
            triggered_by_id=triggered_by_id,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        
        return log
    
    async def get_automation_logs_by_guild(
        self,
        guild_id: int,
        action_type: Optional[str] = None,
        ticket_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[AutomationLog]:
        """Get automation logs for a guild."""
        query = select(AutomationLog).where(AutomationLog.guild_id == guild_id)
        
        if action_type:
            query = query.where(AutomationLog.action_type == action_type)
        if ticket_id:
            query = query.where(AutomationLog.ticket_id == ticket_id)
        
        query = query.order_by(AutomationLog.created_at.desc()).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
