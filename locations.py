"""
checking whether a job's location is in Canada, the United States, both, or neither.

classify("Toronto, ON; New York, NY") -> countries={"CA","US"}, recognized=True
  - countries empty + recognized=True   -> a place we know is outside Canada/US (dropped)
  - countries empty + recognized=False  -> text we couldn't read, e.g. just "Remote" (dropped, logged)

This is a text heuristic. It handles the common formats but not everything; the bot
logs locations it couldn't read so you can see what's being missed.
"""
import re
from collections import namedtuple

LocationResult = namedtuple("LocationResult", "countries recognized")


def _words(items):
    ordered = sorted(set(items), key=len, reverse=True)
    return re.compile(r"(?<![a-z])(?:" + "|".join(re.escape(w) for w in ordered) + r")(?![a-z])")


# ----------------------------------------------------------------------------- Canada
_CA_PROVINCES = ["alberta", "british columbia", "manitoba", "new brunswick", "newfoundland",
                 "labrador", "nova scotia", "ontario", "prince edward island", "quebec", "québec",
                 "saskatchewan", "yukon", "northwest territories", "nunavut"]
_CA_ABBR = ["ab", "bc", "mb", "nb", "nl", "ns", "nt", "nu", "on", "pe", "pei", "qc", "sk", "yt"]
_CA_CITIES = ["toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary", "edmonton",
              "waterloo", "kitchener", "mississauga", "brampton", "markham", "burnaby", "surrey",
              "winnipeg", "halifax", "saskatoon", "regina", "quebec city", "oakville",
              "richmond hill", "vaughan", "laval", "gatineau", "guelph", "kelowna", "fredericton",
              "moncton", "st. john's", "north york", "scarborough", "etobicoke", "new westminster",
              "langley", "abbotsford", "nanaimo", "lethbridge", "red deer", "barrie"]

# ----------------------------------------------------------------------------- United States
_US_STATES = ["alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
              "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
              "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
              "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada",
              "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
              "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
              "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
              "washington", "west virginia", "wisconsin", "wyoming", "district of columbia",
              "puerto rico", "washington d.c."]
_US_ABBR = ["al", "ak", "az", "ar", "ca", "co", "ct", "de", "dc", "fl", "ga", "hi", "id", "il", "in",
            "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh",
            "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
            "vt", "va", "wa", "wv", "wi", "wy", "pr"]
_US_WORDS = ["united states of america", "united states", "usa", "u.s.a", "u.s.", "u.s", "us"]
_US_CITIES = ["new york city", "nyc", "manhattan", "brooklyn", "san francisco", "south san francisco",
              "san jose", "sunnyvale", "mountain view", "palo alto", "menlo park", "redwood city",
              "santa clara", "cupertino", "oakland", "fremont", "san mateo", "foster city",
              "burlingame", "los angeles", "santa monica", "culver city", "irvine", "san diego",
              "seattle", "bellevue", "redmond", "kirkland", "portland", "austin", "dallas", "houston",
              "san antonio", "plano", "irving", "atlanta", "miami", "orlando", "tampa", "boston",
              "chicago", "denver", "boulder", "salt lake city", "phoenix", "scottsdale", "tempe",
              "las vegas", "minneapolis", "detroit", "ann arbor", "pittsburgh", "philadelphia",
              "arlington", "reston", "mclean", "raleigh", "durham", "charlotte", "nashville",
              "columbus", "cleveland", "cincinnati", "indianapolis", "kansas city", "st. louis",
              "saint louis", "milwaukee", "baltimore", "sacramento", "santa barbara", "new orleans",
              "honolulu", "anchorage"]

# ----------------------------------------------------------------------------- everywhere else
_FOREIGN_COUNTRIES = [
    "united kingdom", "uk", "england", "scotland", "wales", "northern ireland", "ireland", "india",
    "germany", "france", "spain", "italy", "netherlands", "poland", "portugal", "sweden", "norway",
    "denmark", "finland", "switzerland", "austria", "belgium", "czech republic", "czechia",
    "romania", "hungary", "greece", "turkey", "israel", "united arab emirates", "uae",
    "saudi arabia", "egypt", "south africa", "nigeria", "kenya", "brazil", "mexico", "argentina",
    "chile", "colombia", "costa rica", "uruguay", "panama", "china", "japan", "south korea",
    "korea", "singapore", "malaysia", "thailand", "vietnam", "philippines", "indonesia", "taiwan",
    "hong kong", "australia", "new zealand", "pakistan", "bangladesh", "sri lanka", "ukraine",
    "russia", "serbia", "bulgaria", "croatia", "lithuania", "latvia", "estonia", "slovakia",
    "slovenia", "luxembourg", "morocco", "ghana", "emea", "apac", "latam", "europe",
    "european union", "asia", "africa", "middle east", "latin america", "south america",
    "central america",
]
_FOREIGN_CITIES = [
    "london", "dublin", "paris", "berlin", "munich", "hamburg", "frankfurt", "amsterdam",
    "rotterdam", "madrid", "barcelona", "lisbon", "porto", "warsaw", "krakow", "wroclaw",
    "stockholm", "gothenburg", "copenhagen", "oslo", "helsinki", "zurich", "geneva", "vienna",
    "prague", "budapest", "bucharest", "athens", "istanbul", "tel aviv", "jerusalem", "bangalore",
    "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "new delhi", "gurgaon", "gurugram",
    "chennai", "noida", "kolkata", "ahmedabad", "tokyo", "osaka", "seoul", "shanghai", "beijing",
    "shenzhen", "guangzhou", "taipei", "sydney", "melbourne", "brisbane", "perth", "auckland",
    "sao paulo", "são paulo", "rio de janeiro", "buenos aires", "mexico city", "guadalajara",
    "monterrey", "bogota", "bogotá", "medellin", "santiago", "lima", "hanoi", "ho chi minh",
    "saigon", "manila", "jakarta", "kuala lumpur", "bangkok", "dubai", "abu dhabi", "riyadh",
    "cairo", "lagos", "nairobi", "johannesburg", "cape town", "kyiv", "kiev", "tbilisi", "cork",
    "galway", "edinburgh", "glasgow", "manchester", "birmingham", "cardiff", "belfast", "bristol",
    "leeds", "rome", "milan", "naples", "florence", "valencia", "moscow", "odessa",
]
# Foreign names that are also US town names ("Dublin, CA", "Paris, TX", "Vienna, VA"):
_AMBIGUOUS_FOREIGN = {"dublin", "paris", "athens", "rome", "vienna", "berlin", "moscow", "lima",
                      "cairo", "valencia", "florence", "milan", "naples", "geneva", "warsaw",
                      "odessa", "manchester", "birmingham", "bristol", "santiago"}
# US state codes that are ALSO common country codes, so "Pune, IN" must not be read as Indiana:
_COLLIDING_CODES = {"de", "in", "co", "pa", "il", "md", "ar", "al", "id", "ma"}

_CA_EXPLICIT_RE = _words(["canada", "canadian"] + _CA_PROVINCES)
_CA_ABBR_RE = re.compile(r",\s*(?:" + "|".join(_CA_ABBR) + r")(?![a-z\-])")
_CA_CODE_RE = re.compile(r"^\s*(?:ca|can)\s*[,\-.\s]\s*(?:" + "|".join(_CA_ABBR) + r")(?![a-z])|^\s*can(?![a-z])")
_CA_CITY_RE = _words(_CA_CITIES)
_US_EXPLICIT_RE = _words(_US_WORDS + _US_STATES)
_US_ABBR_RE = re.compile(r",\s*(" + "|".join(_US_ABBR) + r")(?![a-z\-])")
_US_CITY_RE = _words(_US_CITIES)
_FOREIGN_RE = _words(_FOREIGN_COUNTRIES + _FOREIGN_CITIES)
_SPLIT_RE = re.compile(r"[;|/&•·\n]+")
_MULTI_RE = re.compile(r"^\s*\d+\s+locations?\s*$", re.I)


def _segment(seg: str):
    s = seg.lower().replace("–", "-").replace("—", "-").strip()
    if not s:
        return set(), False
    s_foreign = s.replace("new mexico", " ")
    out = set()
    if "north america" in s:
        out |= {"CA", "US"}
    if _CA_EXPLICIT_RE.search(s) or _CA_ABBR_RE.search(s) or _CA_CODE_RE.search(s):
        out.add("CA")
    if _US_EXPLICIT_RE.search(s):
        out.add("US")
    if out:
        return out, True

    foreign_hits = {m.group(0) for m in _FOREIGN_RE.finditer(s_foreign)}
    abbrs = _US_ABBR_RE.findall(s)
    if foreign_hits:
        # "Dublin, CA" / "Paris, TX": a US-looking town name with a clear US state code
        if foreign_hits <= _AMBIGUOUS_FOREIGN and any(a not in _COLLIDING_CODES for a in abbrs):
            return {"US"}, True
        return set(), True
    if abbrs:
        return {"US"}, True
    ca_city, us_city = bool(_CA_CITY_RE.search(s)), bool(_US_CITY_RE.search(s))
    if ca_city or us_city:
        return ({"CA"} if ca_city else set()) | ({"US"} if us_city else set()), True
    return set(), False


def classify(text) -> LocationResult:
    countries, recognized = set(), False
    for seg in _SPLIT_RE.split(text or ""):
        c, r = _segment(seg)
        countries |= c
        recognized = recognized or r
    return LocationResult(frozenset(countries), recognized)


def classify_job(job: dict) -> LocationResult:
    """Uses job['location']; for Workday's '2 Locations' (or unreadable text) falls back to job['location_hint']."""
    loc = job.get("location") or ""
    hint = job.get("location_hint") or ""
    res = LocationResult(frozenset(), False) if _MULTI_RE.match(loc) else classify(loc)
    if not res.countries and not res.recognized and hint:
        res = classify(hint)
    return res


def display_location(job: dict) -> str:
    loc = job.get("location") or "Unknown"
    hint = job.get("location_hint") or ""
    if _MULTI_RE.match(loc) and hint:
        return f"{loc} (incl. {hint})"
    return loc