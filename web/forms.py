from pipeline.spec import SearchSpec


def _int(form, name):
    v = form.get(name)
    if v in (None, ""):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def build_spec(form) -> SearchSpec:
    rooms = [int(x) for x in form.getlist("rooms") if str(x).isdigit()]
    features = [f for f in form.getlist("features") if f]
    keywords = [k.strip() for k in (form.get("keywords") or "").split(",") if k.strip()]
    pmin = _int(form, "price_min")
    pmax = _int(form, "price_max")
    spec = SearchSpec(
        woj=form.get("woj", ""), miasto=form.get("miasto", ""),
        dzielnica=form.get("dzielnica", ""), rooms=rooms,
        price_min=pmin if pmin is not None else 0,
        price_max=pmax if pmax is not None else 10_000_000,
        area_min=_int(form, "area_min"), area_max=_int(form, "area_max"),
        year_min=_int(form, "year_min"), floor=_int(form, "floor"),
        required_features=features, keywords=keywords,
        rynek=form.get("rynek", "any"),
    )
    return spec.normalized()
