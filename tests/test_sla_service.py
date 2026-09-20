"""
Tests for SLA service.
"""

import pytest
from datetime import datetime, timezone, timedelta

from bot.services.sla_service import SLAService, get_sla_service
from bot.models.ticket import TicketPriority


@pytest.mark.asyncio
async def test_get_sla_target():
    """Test getting SLA target times."""
    service = SLAService()
    
    # Test default targets
    urgent_first_response = await service.get_sla_target(0, "urgent", "first_response")
    assert urgent_first_response == 15  # Default for urgent
    
    medium_resolution = await service.get_sla_target(0, "medium", "resolution")
    assert medium_resolution == 1440  # Default for medium (24 hours)


@pytest.mark.asyncio
async def test_service_singleton():
    """Test that the service singleton works correctly."""
    service1 = get_sla_service()
    service2 = get_sla_service()
    
    assert service1 is service2  # Should be the same instance


def test_default_sla_targets():
    """Test that default SLA targets are properly configured."""
    service = SLAService()
    
    # Check that all priorities have targets configured
    assert TicketPriority.URGENT in service.default_sla_targets
    assert TicketPriority.HIGH in service.default_sla_targets
    assert TicketPriority.MEDIUM in service.default_sla_targets
    assert TicketPriority.LOW in service.default_sla_targets
    
    # Check that each has both first_response and resolution targets
    for priority, targets in service.default_sla_targets.items():
        assert "first_response" in targets
        assert "resolution" in targets
        assert isinstance(targets["first_response"], int)
        assert isinstance(targets["resolution"], int)
