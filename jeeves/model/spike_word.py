from typing import Dict, Optional, Union

import attr

from jeeves.model.spike_categories import SpikeCategory


@attr.s(kw_only=True)
class SpikeWord:
    word: str = attr.ib()
    score: float = attr.ib()
    date: str = attr.ib()
    lang: str = attr.ib()
    spike_group: Optional[SpikeCategory] = attr.ib()
    confirmed: bool = attr.ib(default=False)
    user_id: Optional[int] = attr.ib(default=None)
    summary: Optional[str] = attr.ib(default=None)
    is_bug: Optional[bool] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, spike_dict):
        return cls(
            word=spike_dict["word"],
            score=spike_dict["score"],
            date=spike_dict["date"],
            lang=spike_dict["lang"],
            spike_group=SpikeCategory[spike_dict["spike_group"]],
            confirmed=spike_dict["confirmed"] if "confirmed" in spike_dict else False,
            user_id=spike_dict["user_id"] if "user_id" in spike_dict else None,
            summary=spike_dict["summary"] if "summary" in spike_dict else None,
            is_bug=spike_dict["is_bug"] if "is_bug" in spike_dict else True,
        )

    def to_dict(self) -> Dict[str, Union[float, str]]:
        return {
            "word": self.word,
            "score": self.score,
            "date": self.date,
            "lang": self.lang,
            "spike_group": self.spike_group.name,
            "confirmed": self.confirmed,
            "user_id": self.user_id,
            "summary": self.summary,
            "is_bug": self.is_bug,
        }

    def get_spike_id(self) -> str:
        return f"SPIKE_{self.word}_{self.lang}_{self.date}_{self.spike_group.name}"
