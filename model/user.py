from dataclasses import dataclass
from typing import Tuple

@dataclass
class User():
    user_id: str
    user_gender: str
    age_group: str
    country: str
    interests: Tuple[str,...] # 0, 1 o 2 interessi

    def __hash__(self):
        return hash(self.user_id)

    def __eq__(self, other):
        return self.user_id == other.user_id

    def __str__(self):
        return f"{self.user_id} - {self.user_gender} - {self.age_group} - {self.country} - {self.interests}"