#!/usr/bin/env python3
"""
测试星座运势服务
"""

import pytest
import asyncio
from src.contexts.knowledge.services.horoscope_service import (
    HoroscopeService,
    ZodiacSign,
    HoroscopePeriod,
)


@pytest.mark.asyncio
async def test_get_daily_fortune():
    """测试获取每日运势"""
    service = HoroscopeService()
    data = await service.get_daily_fortune(ZodiacSign.LEO)
    
    assert data.sign == ZodiacSign.LEO
    assert data.period == HoroscopePeriod.DAILY
    assert data.fortune.overall >= 1 and data.fortune.overall <= 100
    assert data.summary is not None
    assert data.advice is not None


@pytest.mark.asyncio
async def test_get_sign_by_date():
    """测试根据日期获取星座"""
    service = HoroscopeService()
    
    # 狮子座 (7/23 - 8/22)
    assert service.get_sign_by_date(8, 1) == ZodiacSign.LEO
    
    # 水瓶座 (1/20 - 2/18)
    assert service.get_sign_by_date(2, 1) == ZodiacSign.AQUARIUS
    
    # 双鱼座 (2/19 - 3/20)
    assert service.get_sign_by_date(3, 1) == ZodiacSign.PISCES


@pytest.mark.asyncio
async def test_all_zodiac_signs():
    """测试所有星座"""
    service = HoroscopeService()
    
    for sign in ZodiacSign:
        data = await service.get_daily_fortune(sign)
        assert data.sign == sign
        assert data.fortune.overall >= 1 and data.fortune.overall <= 100


if __name__ == "__main__":
    asyncio.run(test_get_daily_fortune())
    asyncio.run(test_get_sign_by_date())
    asyncio.run(test_all_zodiac_signs())
    print("All tests passed!")
