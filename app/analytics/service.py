from datetime import date

from app.analytics.schemas import AgeDistribution, AnalyticsSummary
from app.animals.models import AnimalType
from app.animals.repository import AnimalRepository


def _age_years(dob: date, today: date) -> int:
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return max(years, 0)


class AnalyticsService:
    """Assembles the analytics summary from repository counts/aggregates."""

    def __init__(self, repo: AnimalRepository) -> None:
        self.repo = repo

    def summary(self, type_: AnimalType | None = None) -> AnalyticsSummary:
        today = date.today()
        births = self.repo.age_aggregates(type_)
        ages = [_age_years(dob, today) for dob in births]

        calf = sum(1 for a in ages if a < 1)
        young = sum(1 for a in ages if 1 <= a <= 2)
        adult = sum(1 for a in ages if a > 2)
        average = round(sum(ages) / len(ages), 1) if ages else 0.0

        return AnalyticsSummary(
            total=self.repo.total(type_),
            active_total=self.repo.active_total(type_),
            by_status=self.repo.count_by_status(type_),
            by_breed=self.repo.count_by_breed(type_),
            by_gender=self.repo.count_by_gender(type_),
            age_distribution=AgeDistribution(calf=calf, young=young, adult=adult),
            average_age_years=average,
        )
