import re
import unicodedata
from pipeline.spec import SearchSpec

FIVE_PLUS_RX = re.compile(r"\b([5-9]|1\d)\s*[- ]?\s*pok", re.I)
FOUR_RX = re.compile(r"\b4\s*[- ]?\s*pok", re.I)

# ----------------------------------------------------------------------------- parsowanie cech
GARDEN_RX = re.compile(r"ogr[oó]d(?:ek|ku|kiem|kowy|em)?\b|ogr[oó]dk", re.I)
NOT_GARDEN_RX = re.compile(r"ogrodzeni|ogrzewani", re.I)
PARK_RX = re.compile(r"miejsc\w*\s+(?:postojow|parkingow)|parkingow|gara[żz]|hala\s+gara|stanowisk\w*\s+postojow", re.I)
AC_RX = re.compile(r"klimatyzac", re.I)
KOM_RX = re.compile(r"kom[oó]rk\w*\s+lokatorsk|kom[oó]rka|piwnic", re.I)
YEAR_RX = re.compile(r"(?:rok\s+budowy|wybudowan\w*\s+w\s+roku|z\s+roku|budynek\s+z)\D{0,12}(19\d\d|20[0-3]\d)", re.I)

def find_address(text):
    """Zwraca (street, number|None). Szuka ul./al./os. + Nazwa + numer."""
    t = re.sub(r"\s+", " ", text)
    pat = re.compile(
        r"\b(?:ul\.|ulica|al\.|aleja|alei|os\.|osiedle|pl\.|plac)\s+"
        r"([A-ZŁŚŻŹĆŃÓ][\wąćęłńóśżź.\-]+(?:\s+[A-ZŁŚŻŹĆŃÓ0-9][\wąćęłńóśżź.\-]+){0,2})"
        r"\s*(\d+[A-Za-z]?)?", re.U)
    m = pat.search(t)
    if not m: return (None, None)
    street = m.group(1).strip(" .,-")
    street = re.sub(r"\s+(na|w|przy|os|ul|nr)$", "", street, flags=re.I).strip()
    return (street, m.group(2))

# kwoty: dopłata za parking / komórkę
def paid_extra(text, kind):
    """Zwraca dopłatę (zł) za parking/komórkę jeśli płatne osobno; 0 gdy w cenie/brak."""
    rx = PARK_RX if kind == "park" else KOM_RX
    for m in rx.finditer(text):
        seg = text[max(0, m.start() - 40): m.end() + 120].lower()
        if re.search(r"w\s+cenie|wliczon|gratis|w\s+ramach", seg):
            return 0
        if re.search(r"dodatkow|dop[lł]at|osobn|p[lł]atn|\+\s*\d|do\s+kupieni|do\s+nabyci|mo[zż]liwo[sś][cć]\s+(?:do)?kup", seg):
            am = re.search(r"(\d[\d  .]{3,})\s*(?:z[lł]|pln|tys)", seg)
            if am:
                v = int(re.sub(r"[  .]", "", am.group(1)))
                if "tys" in seg[am.start():am.end()+4]: v *= 1000
                if 3000 <= v <= 400000: return v
    return 0

def num(s):
    d = re.sub(r"[^\d]", "", str(s or ""))
    return int(d) if d else 0

def enrich(r):
    text = r["text"]
    ext = r.get("extras", [])
    floor = r.get("floor")
    # OGRÓD: tylko parter/0 (wyższe piętra ⇒ brak ogrodu). Tekst łapie generyczny marketing
    # ("balkony LUB ogródki", "mieszkania z ogródkiem") → fałszywki, więc:
    #  - Otodom: ufaj strukturze (extras 'garden' lub terrain>0), NIE tekstowi,
    #  - OLX: brak struktury → wymagaj parteru + tekstu.
    text_garden = bool(GARDEN_RX.search(text)) and not NOT_GARDEN_RX.search(text)
    if r["src"] == "Otodom":
        gsig = ("garden" in ext) or (r.get("terrain", 0) > 0)
    else:
        gsig = text_garden and floor == 0
    r["garden"] = gsig and (floor is None or floor <= 0)
    r["parking"] = ("garage" in ext or "parking" in ext) or bool(PARK_RX.search(text))
    r["aircon"] = ("air_conditioning" in ext) or bool(AC_RX.search(text))
    r["komorka"] = ("basement" in ext) or bool(KOM_RX.search(text))
    if not r.get("year"):
        m = YEAR_RX.search(text)
        r["year"] = int(m.group(1)) if m else None
    if not r.get("market"):
        r["market"] = "wtorny"
    r["secondary"] = r["market"].startswith(("wt", "sec"))
    # adres
    if not r.get("street"):
        st, nzb = find_address(text)
        r["street"], r["number"] = st, nzb
    r["park_extra"] = paid_extra(text, "park")
    r["kom_extra"] = paid_extra(text, "kom")
    r["eff_price"] = r["price"] + r["park_extra"] + r["kom_extra"]
    return r

ROOM_WORDS = {1: ("1", "one", "1 pokój", "kawalerka"),
              2: ("2", "two", "2 pokoje"),
              3: ("3", "three", "3 pokoje"),
              4: ("4", "four", "4 pokoje", "4 i więcej"),
              5: ("5", "five", "5 pokoi", "5 i więcej")}

def _rooms_to_int(raw) -> int | None:
    s = str(raw or "").strip().lower()
    for n, words in ROOM_WORDS.items():
        if s in words:
            return n
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None

def _room_count(r):
    raw = str(r.get("rooms") or "").strip().lower()
    if r.get("src") == "OLX" and ("więcej" in raw or "wiecej" in raw):  # OLX 4+ bucket
        text = r.get("text", "")
        m = FIVE_PLUS_RX.search(text)
        if m and not FOUR_RX.search(text):
            return int(m.group(1))
        return 4
    return _rooms_to_int(raw)

def keywords_match(text: str, keywords: list[str]) -> bool:
    def normalize(s):
        s = (s or "").lower()
        s = unicodedata.normalize('NFD', s)
        return ''.join(c for c in s if unicodedata.category(c) != 'Mn')

    t = normalize(text)
    return all(normalize(k) in t for k in keywords)

def qualifies(r: dict, spec: SearchSpec) -> bool:
    if spec.rooms:
        rn = _room_count(r)
        if rn is None or rn not in spec.rooms:
            return False
    if not (r["price"] and r["area"]):
        return False
    if not (spec.price_min <= r["price"] <= spec.price_max):
        return False
    if spec.area_min is not None and r["area"] < spec.area_min:
        return False
    if spec.area_max is not None and r["area"] > spec.area_max:
        return False
    if spec.year_min is not None and r.get("year") and r["year"] < spec.year_min:
        return False
    if spec.floor is not None and r.get("floor") is not None and r["floor"] != spec.floor:
        return False
    feat = {"ogrod": r["garden"], "parking": r["parking"],
            "klimatyzacja": r["aircon"], "komorka": r["komorka"]}
    if any(not feat[f] for f in spec.required_features):
        return False
    if spec.rynek == "pierwotny" and r["secondary"]:
        return False
    if spec.rynek == "wtorny" and not r["secondary"]:
        return False
    if spec.keywords and not keywords_match(r["text"], spec.keywords):
        return False
    return True
