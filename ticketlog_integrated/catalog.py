"""KOPIS 공연 목록 → 상세 → 예매처별 표. 원본 노트북의 API 흐름을 유지한다."""
from datetime import date, timedelta
from urllib.parse import urlsplit
import re
import requests
import pandas as pd
from defusedxml.ElementTree import fromstring

BASE = 'https://www.kopis.or.kr/openApi/restful/pblprfr'
COLUMNS = ['performance_id','title','venue','period','poster','genre','vendor','url','demo']


def web_url(value):
    value = (value or '').strip()
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in ('http','https') and parsed.hostname and not parsed.username and not parsed.password else ''
    except ValueError:
        return ''


def parse_rows(xml):
    root = fromstring(xml)
    if root.tag != 'dbs' or root.find('error') is not None or root.find('errMsg') is not None:
        raise ValueError('KOPIS 응답 형식 오류')
    return root.findall('db')


def text(node, key, default=''):
    return (node.findtext(key) or default).strip()


def get_xml(session, url, params):
    response = session.get(url, params=params, timeout=(4, 9))
    response.raise_for_status()
    return parse_rows(response.content)


def fetch_kopis_data(api_key, start, end, count=5):
    if not api_key or not 1 <= count <= 10 or end < start or (end-start).days > 30:
        raise ValueError('API 키 및 조회 기간을 확인해 주세요.')
    rows = []
    failures = 0
    with requests.Session() as session:
        session.headers.update({'User-Agent':'TicketLog-EducationalProject/1.0','Accept':'application/xml,text/xml'})
        items = get_xml(session, BASE, {'service':api_key,'stdate':start.strftime('%Y%m%d'),'eddate':end.strftime('%Y%m%d'),'cpage':1,'rows':count})
        for item in items[:count]:
            pid = text(item,'mt20id')
            if not re.fullmatch(r'PF\d+',pid):
                failures += 1
                continue
            try:
                details = get_xml(session, BASE+'/'+pid, {'service':api_key})
                if not details:
                    failures += 1
                    continue
                db = details[0]
            except Exception:
                # 예외 원문에는 API 키가 포함될 수 있으므로 공개 화면에 표시하지 않는다.
                failures += 1
                continue
            basic = dict(performance_id=pid,title=text(db,'prfnm','공연명 미상'),venue=text(db,'fcltynm','장소 미정'),period=f"{text(db,'prfpdfrom')} ~ {text(db,'prfpdto')}",poster=web_url(text(db,'poster')),genre=text(db,'genrenm','기타'),demo=False)
            vendors = db.findall('./relates/relate')
            if vendors:
                for v in vendors:
                    rows.append(dict(basic,vendor=text(v,'relatenm','예매처 미상'),url=web_url(text(v,'relateurl'))))
            else:
                rows.append(dict(basic,vendor='미등록',url=''))
    return pd.DataFrame(rows, columns=COLUMNS).drop_duplicates(subset=['performance_id','vendor','url']), failures


def demo_catalog(today):
    data=[]
    for i,(title,genre,venue) in enumerate([('달빛 극장의 비밀','뮤지컬','예시 아트홀'),('푸른 밤 라이브','대중음악','예시 콘서트홀'),('별의 오케스트라','서양음악(클래식)','예시 음악당'),('봄날의 무대','연극','예시 소극장')]):
        start=today+timedelta(days=20+i*3)
        data.append(dict(performance_id=f'DEMO-{i+1}',title='[시연] '+title,genre=genre,venue=venue,period=f'{start} ~ {start+timedelta(days=2)}',poster='',vendor='시연 예매처',url='',demo=True))
    return pd.DataFrame(data,columns=COLUMNS)
