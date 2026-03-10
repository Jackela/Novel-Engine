#!/usr/bin/env python3
"""
Horoscope API Router - 星座运势API路由

提供星座运势查询的REST API端点。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.contexts.knowledge.services.horoscope_service import (
    HoroscopeData,
    HoroscopeService,
    ZodiacSign,
)

router = APIRouter(
    prefix="/api/horoscope",
    tags=["horoscope", "星座运势"],
    responses={404: {"description": "Not found"}},
)


class FortuneResponse(BaseModel):
    """运势响应模型"""

    overall: int = Field(..., description="综合运势 (1-100)", ge=1, le=100)
    love: int = Field(..., description="爱情运势", ge=1, le=100)
    career: int = Field(..., description="事业运势", ge=1, le=100)
    wealth: int = Field(..., description="财富运势", ge=1, le=100)
    health: int = Field(..., description="健康运势", ge=1, le=100)


class HoroscopeResponse(BaseModel):
    """星座运势响应模型"""

    sign: str = Field(..., description="星座英文名")
    sign_cn: str = Field(..., description="星座中文名")
    period: str = Field(..., description="查询周期")
    date: str = Field(..., description="日期")
    fortune: FortuneResponse = Field(..., description="运势详情")
    summary: str = Field(..., description="运势总结")
    advice: str = Field(..., description="建议")
    lucky_number: Optional[int] = Field(None, description="幸运数字")
    lucky_color: Optional[str] = Field(None, description="幸运颜色")
    lucky_direction: Optional[str] = Field(None, description="幸运方位")


# 星座中文名映射
SIGN_NAME_MAP = {
    ZodiacSign.ARIES: "白羊座",
    ZodiacSign.TAURUS: "金牛座",
    ZodiacSign.GEMINI: "双子座",
    ZodiacSign.CANCER: "巨蟹座",
    ZodiacSign.LEO: "狮子座",
    ZodiacSign.VIRGO: "处女座",
    ZodiacSign.LIBRA: "天秤座",
    ZodiacSign.SCORPIO: "天蝎座",
    ZodiacSign.SAGITTARIUS: "射手座",
    ZodiacSign.CAPRICORN: "摩羯座",
    ZodiacSign.AQUARIUS: "水瓶座",
    ZodiacSign.PISCES: "双鱼座",
}


def _convert_to_response(data: HoroscopeData) -> HoroscopeResponse:
    """将服务数据转换为API响应"""
    return HoroscopeResponse(
        sign=data.sign.value,
        sign_cn=SIGN_NAME_MAP.get(data.sign, data.sign.value),
        period=data.period.value,
        date=data.date,
        fortune=FortuneResponse(
            overall=data.fortune.overall,
            love=data.fortune.love,
            career=data.fortune.career,
            wealth=data.fortune.wealth,
            health=data.fortune.health,
        ),
        summary=data.summary,
        advice=data.advice,
        lucky_number=data.lucky_number,
        lucky_color=data.lucky_color,
        lucky_direction=data.lucky_direction,
    )


@router.get("/daily/{sign}", response_model=HoroscopeResponse)
async def get_daily_horoscope(
    sign: ZodiacSign,
    date: Optional[str] = Query(None, description="日期 (YYYY-MM-DD, 默认今天)"),
):
    """
    获取每日星座运势

    - **sign**: 星座 (aries, taurus, gemini, cancer, leo, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces)
    - **date**: 可选，日期格式 YYYY-MM-DD
    """
    service = HoroscopeService()
    data = await service.get_daily_fortune(sign, date)
    return _convert_to_response(data)


@router.get("/weekly/{sign}", response_model=HoroscopeResponse)
async def get_weekly_horoscope(
    sign: ZodiacSign,
    week: Optional[str] = Query(None, description="周次 (YYYY-WNN, 默认本周)"),
):
    """
    获取每周星座运势

    - **sign**: 星座
    - **week**: 可选，周次格式 YYYY-WNN (如 2024-W01)
    """
    service = HoroscopeService()
    data = await service.get_weekly_fortune(sign, week)
    return _convert_to_response(data)


@router.get("/monthly/{sign}", response_model=HoroscopeResponse)
async def get_monthly_horoscope(
    sign: ZodiacSign,
    month: Optional[str] = Query(None, description="月份 (YYYY-MM, 默认本月)"),
):
    """
    获取每月星座运势

    - **sign**: 星座
    - **month**: 可选，月份格式 YYYY-MM
    """
    service = HoroscopeService()
    data = await service.get_monthly_fortune(sign, month)
    return _convert_to_response(data)


@router.get("/yearly/{sign}", response_model=HoroscopeResponse)
async def get_yearly_horoscope(
    sign: ZodiacSign,
    year: Optional[str] = Query(None, description="年份 (YYYY, 默认今年)"),
):
    """
    获取每年星座运势

    - **sign**: 星座
    - **year**: 可选，年份格式 YYYY
    """
    service = HoroscopeService()
    data = await service.get_yearly_fortune(sign, year)
    return _convert_to_response(data)


@router.get("/by-birthday", response_model=HoroscopeResponse)
async def get_horoscope_by_birthday(
    month: int = Query(..., description="出生月份 (1-12)", ge=1, le=12),
    day: int = Query(..., description="出生日期 (1-31)", ge=1, le=31),
):
    """
    根据生日获取今日运势

    - **month**: 出生月份 (1-12)
    - **day**: 出生日期 (1-31)
    """
    service = HoroscopeService()
    sign = service.get_sign_by_date(month, day)
    data = await service.get_daily_fortune(sign)
    return _convert_to_response(data)


@router.get("/signs")
async def list_zodiac_signs():
    """获取所有星座列表"""
    return {
        "signs": [
            {
                "key": sign.value,
                "name": SIGN_NAME_MAP[sign],
                "date_range": _get_date_range(sign),
            }
            for sign in ZodiacSign
        ]
    }


def _get_date_range(sign: ZodiacSign) -> str:
    """获取星座日期范围"""
    date_ranges = {
        ZodiacSign.ARIES: "3/21 - 4/19",
        ZodiacSign.TAURUS: "4/20 - 5/20",
        ZodiacSign.GEMINI: "5/21 - 6/21",
        ZodiacSign.CANCER: "6/22 - 7/22",
        ZodiacSign.LEO: "7/23 - 8/22",
        ZodiacSign.VIRGO: "8/23 - 9/22",
        ZodiacSign.LIBRA: "9/23 - 10/23",
        ZodiacSign.SCORPIO: "10/24 - 11/22",
        ZodiacSign.SAGITTARIUS: "11/23 - 12/21",
        ZodiacSign.CAPRICORN: "12/22 - 1/19",
        ZodiacSign.AQUARIUS: "1/20 - 2/18",
        ZodiacSign.PISCES: "2/19 - 3/20",
    }
    return date_ranges.get(sign, "Unknown")
