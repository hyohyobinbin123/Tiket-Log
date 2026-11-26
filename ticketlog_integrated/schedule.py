"""한국 시각, 월별 달력, 일정 집계 — 두 노트북의 핵심 로직."""
import calendar
from collections import Counter
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
KST = ZoneInfo('Asia/Seoul')
STATUSES = ['예매 예정','구매 완료','구매 실패','취소']

def now_kst():
    return datetime.now(KST)

def local_dt(value):
    dt = datetime.fromisoformat(value.replace('Z','+00:00'))
    return dt.replace(tzinfo=KST) if dt.tzinfo is None else dt.astimezone(KST)

def month_grid(year, month):
    return calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)

def day_counts(rows):
    return Counter(local_dt(row['opening_at']).date() for row in rows)

def upcoming(rows, now):
    return sorted([r for r in rows if r['status']=='예매 예정' and local_dt(r['opening_at']) >= now],key=lambda r:local_dt(r['opening_at']))

def dday(value, now):
    dt=local_dt(value)
    if dt < now: return '오픈 지남'
    days=(dt.date()-now.date()).days
    return 'D-Day' if days==0 else f'D-{days}'

def filter_rows(rows, keyword='', vendor='전체', genre='전체', selected=None, hide_past=False, now=None):
    kw=keyword.strip().casefold()
    now=now or now_kst()
    return sorted([r for r in rows if (not kw or kw in ' '.join(str(r.get(k,'')) for k in ['title','vendor','venue']).casefold()) and (vendor=='전체' or r['vendor']==vendor) and (genre=='전체' or r['genre']==genre) and (selected is None or local_dt(r['opening_at']).date()==selected) and (not hide_past or local_dt(r['opening_at'])>=now)],key=lambda r:local_dt(r['opening_at']))
