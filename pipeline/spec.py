from dataclasses import dataclass, field

FEATURE_KEYS = ("ogrod", "parking", "klimatyzacja", "komorka")
RYNEK_VALS = ("pierwotny", "wtorny", "any")

@dataclass
class SearchSpec:
    woj: str
    miasto: str
    rooms: list[int]
    dzielnica: str = ""
    price_min: int = 0
    price_max: int = 10_000_000
    area_min: float | None = None
    area_max: float | None = None
    year_min: int | None = None
    floor: int | None = None
    required_features: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    rynek: str = "any"
    sort: str = "value"

    def normalized(self) -> "SearchSpec":
        self.woj = (self.woj or "").strip().lower()
        self.miasto = (self.miasto or "").strip().lower()
        self.dzielnica = (self.dzielnica or "").strip().lower()
        self.required_features = [f.strip().lower() for f in self.required_features if f.strip()]
        self.keywords = [k.strip().lower() for k in self.keywords if k.strip()]
        self.rynek = (self.rynek or "any").strip().lower()
        bad = set(self.required_features) - set(FEATURE_KEYS)
        if bad:
            raise ValueError(f"unknown required_features: {sorted(bad)}")
        if self.rynek not in RYNEK_VALS:
            raise ValueError(f"rynek must be one of {RYNEK_VALS}")
        return self
