from dataclasses import dataclass


@dataclass
class Segment():
    segment_id: str
    campaign_id: int
    impressions: int
    clicks: int
    engagement: int
    purchases: int
    weight: int
    n_users_reached: int

    def __hash__(self):
        return hash(self.segment_id)

    def __eq__(self, other):
        return self.segment_id == other.segment_id

    def __str__(self):
        return f"{self.segment_id} - {self.n_users_reached}"