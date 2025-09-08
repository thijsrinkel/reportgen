# core/filters.py
from datetime import date, datetime
def datetimeformat(v, fmt="%Y-%m-%d"):
    if isinstance(v, (date, datetime)): return v.strftime(fmt)
    try: return datetime.fromisoformat(str(v)).strftime(fmt)
    except: return v
