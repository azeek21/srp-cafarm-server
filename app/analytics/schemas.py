from pydantic import BaseModel


class AgeDistribution(BaseModel):
    calf: int  # < 1 year
    young: int  # 1–2 years
    adult: int  # > 2 years


class AnalyticsSummary(BaseModel):
    total: int
    active_total: int
    by_status: dict[str, int]
    by_breed: dict[str, int]
    by_gender: dict[str, int]
    age_distribution: AgeDistribution
    average_age_years: float
