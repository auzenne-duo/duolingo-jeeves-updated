from typing import Dict, Optional, Union

import attr

from jeeves.model.spike_categories import SpikeCategory

_DEFAULT_SPIKE_STATUS = "UNCONFIRMED"


@attr.s(kw_only=True)
class SpikeWord:
    word: str = attr.ib()
    score: float = attr.ib()
    date: str = attr.ib()
    lang: str = attr.ib()
    spike_group: Optional[SpikeCategory] = attr.ib()
    confirmed: bool = attr.ib(default=False)
    confirmed_user_id: Optional[int] = attr.ib(default=None)
    email_sent_date: Optional[str] = attr.ib(default=None)
    email_user_id: Optional[int] = attr.ib(default=None)
    fixed: bool = attr.ib(default=False)
    fixed_user_id: Optional[int] = attr.ib(default=None)
    summary: Optional[str] = attr.ib(default=None)
    is_bug: Optional[bool] = attr.ib(default=None)
    experiment_spikes: Optional[Dict[str, int]] = attr.ib(default=None)
    status: Optional[str] = attr.ib(default=_DEFAULT_SPIKE_STATUS)
    status_user_id: Optional[int] = attr.ib(default=None)

    @classmethod
    def from_dict(cls, spike_dict):
        return cls(
            word=spike_dict["word"],
            score=spike_dict["score"],
            date=spike_dict["date"],
            lang=spike_dict["lang"],
            spike_group=SpikeCategory[spike_dict["spike_group"]]
            if spike_dict["spike_group"] in SpikeCategory.__members__
            else None,
            confirmed=spike_dict["confirmed"] if "confirmed" in spike_dict else False,
            confirmed_user_id=spike_dict["confirmed_user_id"]
            if "confirmed_user_id" in spike_dict
            else None,
            email_sent_date=spike_dict["email_sent_date"]
            if "email_sent_date" in spike_dict
            else None,
            email_user_id=spike_dict["email_user_id"] if "email_user_id" in spike_dict else None,
            fixed=spike_dict["fixed"] if "fixed" in spike_dict else False,
            fixed_user_id=spike_dict["fixed_user_id"] if "fixed_user_id" in spike_dict else None,
            summary=spike_dict["summary"] if "summary" in spike_dict else None,
            is_bug=spike_dict["is_bug"] if "is_bug" in spike_dict else True,
            experiment_spikes=spike_dict["experiment_spikes"].to_dict()
            if "experiment_spikes" in spike_dict
            else {},
            status=spike_dict["status"] if "status" in spike_dict else _DEFAULT_SPIKE_STATUS,
            status_user_id=spike_dict["status_user_id"] if "status_user_id" in spike_dict else None,
        )

    def to_dict(self) -> Dict[str, Union[float, str]]:
        return {
            "word": self.word,
            "score": self.score,
            "date": self.date,
            "lang": self.lang,
            "spike_group": self.spike_group.name,
            "confirmed": self.confirmed,
            "confirmed_user_id": self.confirmed_user_id,
            "email_sent_date": self.email_sent_date,
            "email_user_id": self.email_user_id,
            "fixed": self.fixed,
            "fixed_user_id": self.fixed_user_id,
            "summary": self.summary,
            "is_bug": self.is_bug,
            "experiment_spikes": self.experiment_spikes,
            "status": self.status,
            "status_user_id": self.status_user_id,
        }

    def get_spike_id(self) -> str:
        return f"SPIKE_{self.word}_{self.lang}_{self.date}_{self.spike_group.name}"
