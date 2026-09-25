"""Pydantic request/response models."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

Traffic = Literal["Low", "Moderate", "Heavy", "Severe"]
Weather = Literal["Clear", "Rain", "Fog", "Hot", "Cold"]
Area = Literal["Urban", "Dense Urban", "Suburban"]
Load = Literal["Low", "Moderate", "High", "Very High"]
Experience = Literal["New", "Moderate", "Experienced"]
Day = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
Status = Literal["ON TIME", "AT RISK", "DELAY LIKELY"]


class OrderInput(BaseModel):
    """One order, as entered in the manual form (same rules as a CSV row; it goes through the same cleaner)."""

    model_config = ConfigDict(extra="ignore")

    order_id: str = Field(min_length=1, max_length=40, examples=["ZF2048"])
    order_time: str = Field(examples=["20:15"], description="HH:MM (24h) or a full date-time")
    day_of_week: Day
    num_items: int = Field(ge=1, le=60)
    order_value: float = Field(gt=0, le=100_000)
    prep_time: float = Field(ge=0, le=240, description="Restaurant preparation time, minutes")
    restaurant_load: Load
    rider_assignment_delay: float = Field(ge=0, le=180, description="minutes")
    pickup_wait: float = Field(ge=0, le=180, description="minutes")
    distance_km: float = Field(gt=0, le=100)
    traffic_level: Traffic
    weather: Weather
    area_type: Area
    rider_experience: Experience
    peak_hour: Optional[bool] = Field(default=None, description="Derived from order_time when omitted")
    weekend: Optional[bool] = None
    promised_eta: Optional[float] = Field(default=None, gt=0, le=300, description="Minutes; baseline quote is used when omitted")
    batch_delivery: bool = False
    customer_zone: Optional[str] = None
    restaurant_zone: Optional[str] = None

    @field_validator("order_id", "order_time")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class Health(BaseModel):
    status: Literal["ok"]
    models_loaded: bool
    delay_rule: str
    version: str
