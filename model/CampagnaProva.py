from dataclasses import dataclass


@dataclass
class CampagnaProva():
    campaign_id: int
    name: str
    start_date: str
    end_date: str
    duration_days: int
    total_budget: float

    def __hash__(self):
        return hash(self.campaign_id)

    def __eq__(self, other):
        return self.campaign_id == other.campaign_id

    def __str__(self):
        return f"{self.campaign_id} - {self.name}"