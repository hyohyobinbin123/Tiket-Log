"""Ticket Log: KOPIS 탐색, 달력 기반 예매 일정 등록 및 계정별 관리."""
from datetime import date, datetime, time, timedelta
from uuid import uuid4
import os
import re
import pandas as pd
import streamlit as st
from catalog import fetch_kopis_data, demo_catalog, web_url
from schedule import KST, STATUSES, now_kst, local_dt, month_grid, day_counts, upcoming, dday, filter_rows
import db

st.set_page_config(page_title='Ticket Log | 티켓로그',page_icon='🎫',layout='wide')
st.markdown('''<style>
.block-container {max-width: 1120px; padding-top: 2.2rem; padding-bottom: 4rem;}
[data-testid="stSidebar"] {background:#F4F5FB;}
[data-testid="stMetric"] {border:1px solid #E4E5F1;border-radius:16px;padding:16px;background:#fff;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px;}
.hero {background:linear-gradient(120deg,#29245f,#5146c6);border-radius:20px;color:white;padding:26px 30px;margin-bottom:18px;}
.hero p{color:#e2e1ff;margin:4px 0 0}.hero h1{font-size:2rem;margin:5px 0;color:white;line-height:1.3}
</style>''',unsafe_allow_html=True)

def setting(name):
    try: return str(st.secrets.get(name,os.environ.get(name,'')))
    except (FileNotFoundError,KeyError): return os.environ.get(name,'')
    except Exception: return os.environ.get(name,'')

now=now_kst(); today=now.date()
for key, value in {'catalog':pd.DataFrame(), 'catalog_loaded':False,'demo_rows':[], 'selected_day':None, 'flash':'', 'uid':None, 'email':'','client':None}.items():
    if key not in st.session_state: st.session_state[key]=value
s=st.session_state
kopis_key=setting('KOPIS_API_KEY'); url=setting('SUPABASE_URL'); db_key=setting('SUPABASE_KEY')
configured=bool(url and db_key and 'YOUR_' not in url and 'YOUR_' not in db_key)
if configured and s.client is None:
    try: s.client=db.create_session_client(url,db_key)
    except Exception: st.warning('Supabase 연결 설정을 확인해 주세요.')

# 공용 계정이나 비밀번호를 저장하지 않고 브라우저 세션마다 인증 클라이언트를 사용한다.
with st.sidebar:
    st.title('🎫 TICKET LOG')
    st.caption('공연을 발견하고, 예매 일정을 기록하세요.')
    page=st.radio('메뉴',['공연 탐색','예매 달력','내 티켓'],label_visibility='collapsed')
    st.divider()
    if s.uid:
        st.success('로그인 상태')
        st.caption(s.email)
        if st.button('로그아웃',use_container_width=True):
            try: s.client.auth.sign_out()
            except Exception: pass
            s.client=None; s.uid=None; s.email=''; s.selected_day=None
            st.rerun()
    elif s.client is not None:
        mode=st.radio('계정',['로그인','회원가입'],horizontal=True)
        with st.form('account_'+mode,clear_on_submit=True):
            email=st.text_input('이메일')
            password=st.text_input('비밀번호',type='password')
            if mode=='회원가입': st.caption('8자 이상, 영문 대·소문자, 숫자, 특수문자 조합을 권장합니다. 이메일 인증이 필요할 수 있습니다.')
            submitted=st.form_submit_button(mode,use_container_width=True)
        if submitted:
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()): st.error('이메일 주소를 확인해 주세요.')
            elif not password or (mode=='회원가입' and len(password)<8): st.error('비밀번호를 8자 이상 입력해 주세요.' if mode=='회원가입' else '비밀번호를 입력해 주세요.')
            else:
                try:
                    credentials={'email':email.strip(),'password':password}
                    result=s.client.auth.sign_up(credentials) if mode=='회원가입' else s.client.auth.sign_in_with_password(credentials)
                    if result.session and result.user:
                        s.uid=str(result.user.id); s.email=result.user.email or email.strip(); s.flash='로그인되었습니다.'; st.rerun()
                    else: st.info('가입 요청을 처리했습니다. 이메일 인증이 필요하거나 기존 계정일 수 있습니다. 받은 편지함을 확인한 뒤 로그인해 주세요.')
                except Exception as exc: st.error(db.error_message(exc))
    else: st.info('로그인 설정 전입니다. 시연 모드로 체험할 수 있습니다.')
    st.divider()
    demo_mode=st.toggle('가상 데이터 시연 모드',value=not bool(kopis_key),help='실제 공연이나 구매가 아닙니다. 로그인하지 않아도 현재 세션에서 체험할 수 있습니다.')
    if not demo_mode and not kopis_key:
        kopis_key=st.text_input('KOPIS 인증키 (현재 세션만)',type='password')
    st.caption('한국 표준시 · 실제 티켓은 공식 예매처에서 구매합니다.')

st.markdown('<div class="hero"><p>TICKET LOG / 공연 예매 일정 매니저</p><h1>좋아하는 공연, 놓치지 않도록.</h1><p>공연 검색부터 예매 일정 기록, 달력과 내 티켓 관리까지 한곳에서.</p></div>',unsafe_allow_html=True)
if s.flash: st.success(s.flash); s.flash=''
if demo_mode: st.info('시연 모드: 모든 예시 공연은 가상입니다. 일정은 이 브라우저 세션에만 저장되고 실제 예매되지 않습니다.')

# 실제 DB 오류를 빈 목록으로 가장하지 않는다.
rows=[]; storage_ok=True
if demo_mode: rows=s.demo_rows
elif s.uid:
    try: rows=[r for r in db.list_tickets(s.client,s.uid) if not r['demo']]
    except Exception as exc: storage_ok=False; st.error(db.error_message(exc))

can_save=demo_mode or (bool(s.uid) and storage_ok)

def save(data):
    if demo_mode:
        if any(all(r[k]==data[k] for k in ('performance_id','vendor','opening_at')) for r in s.demo_rows): raise ValueError('중복 일정')
        s.demo_rows=[*s.demo_rows,dict(data,id=str(uuid4()))]
    else: db.add_ticket(s.client,s.uid,data)

def modify(rid,changes):
    if demo_mode:
        updated=[dict(r,**changes) if r['id']==rid else r for r in s.demo_rows]
        keys=[(r['performance_id'],r['vendor'],r['opening_at']) for r in updated]
        if len(keys)!=len(set(keys)): raise ValueError('중복 일정')
        s.demo_rows=updated
    else: db.update_ticket(s.client,s.uid,rid,changes)

def remove(rid):
    if demo_mode: s.demo_rows=[r for r in s.demo_rows if r['id']!=rid]
    else: db.delete_ticket(s.client,s.uid,rid)

future=upcoming(rows,now); week=[r for r in future if local_dt(r['opening_at'])<=now+timedelta(days=7)]
a,b,c=st.columns(3)
a.metric('가장 임박한 예매',dday(future[0]['opening_at'],now) if future else '일정 없음',help=future[0]['title']+' · '+local_dt(future[0]['opening_at']).strftime('%m/%d %H:%M') if future else '일정을 등록해 주세요.')
b.metric('7일 이내 예매',f'{len(week)}건'); c.metric('구매 완료',f"{sum(r['status']=='구매 완료' for r in rows)}건")
if future: st.caption('다음 일정: '+future[0]['title']+' · '+local_dt(future[0]['opening_at']).strftime('%m/%d %H:%M')+' KST')

catalog=demo_catalog(today) if demo_mode else s.catalog

@st.cache_data(ttl=3600,max_entries=32,show_spinner=False)
def cached_catalog(key,start,end,count):
    return fetch_kopis_data(key,start,end,count)

def catalog_loader():
    if demo_mode: return demo_catalog(today)
    with st.expander('공연 조회 설정',expanded=not s.catalog_loaded):
        with st.form('kopis_query'):
            c1,c2=st.columns(2)
            start=c1.date_input('공연 조회 시작일',today)
            end=c2.date_input('공연 조회 종료일',today+timedelta(days=30))
            count=st.select_slider('최대 공연 수',options=[3,5,10],value=5)
            clicked=st.form_submit_button('KOPIS 공연 불러오기',type='primary')
        if clicked:
            if not kopis_key: st.warning('KOPIS 키를 Streamlit Secrets 또는 사이드바에 입력해 주세요.')
            elif end<start or (end-start).days>30: st.warning('조회 범위는 최대 31일(시작일 포함)로 설정해 주세요.')
            else:
                try:
                    with st.spinner('공연 및 예매처 정보를 가져오는 중…'):
                        result,failures=cached_catalog(kopis_key,start,end,count)
                    s.catalog=result; s.catalog_loaded=True
                    if failures: st.warning(f'공연 상세 {failures}건을 불러오지 못했습니다.')
                    if result.empty: st.info('조회된 공연이 없습니다. 기간을 변경해 보세요.')
                except Exception: st.error('KOPIS 조회 실패: 인증키, 네트워크 또는 조회 기간을 확인해 주세요. 이전 조회 결과는 유지됩니다.')
    return s.catalog

def register_form(data, day, prefix):
    if data.empty:
        st.info('먼저 공연 탐색에서 KOPIS 공연을 불러오거나 시연 모드를 켜 주세요.'); return
    choices=data[data['vendor']!='미등록'].reset_index(drop=True)
    if choices.empty: st.info('등록할 수 있는 예매처가 없습니다.'); return
    labels=[f"{r.title} · {r.vendor} · {r.venue} ({r.performance_id})" for r in choices.itertuples()]
    idx=st.selectbox('공연 및 예매처',list(range(len(labels))),format_func=lambda i:labels[i],key=prefix+'_choice')
    row=choices.iloc[idx].to_dict()
    if web_url(row['url']): st.link_button('공식 예매처에서 티켓 오픈 일시 확인',row['url'])
    else: st.caption('예매처 링크 없음 · 시연 또는 직접 확인 필요')
    st.caption('공연 및 예매처는 조회된 목록에서 선택하므로 오타를 방지합니다. 공식 예매처에서 확인한 오픈 일시를 입력하세요.')
    with st.form(prefix+'_form'):
        c1,c2=st.columns(2)
        opening=c1.date_input('티켓 오픈 날짜',value=day,key=prefix+'_date')
        clock=c2.time_input('티켓 오픈 시간 (KST)',value=time(20,0),key=prefix+'_time')
        note=st.text_input('메모 (선택)',max_chars=500,placeholder='선예매, 좌석 구역 등')
        ok=st.form_submit_button('내 예매 일정에 등록',type='primary',disabled=not can_save)
    if not can_save: st.info('실제 일정은 로그인하고 데이터베이스 연결을 완료해야 저장됩니다.')
    if ok:
        data={'performance_id':row['performance_id'],'title':row['title'],'venue':row['venue'],'genre':row['genre'],'vendor':row['vendor'],'vendor_url':row['url'],'poster':row['poster'],'performance_period':row['period'],'opening_at':datetime.combine(opening,clock,KST).isoformat(),'status':'예매 예정','note':note,'demo':bool(row['demo'])}
        try: save(data); s.flash='예매 일정이 등록되었습니다. 내 티켓에서 확인하세요.'; st.rerun()
        except ValueError: st.error('이미 등록한 일정입니다.')
        except Exception as exc: st.error(db.error_message(exc))

if page=='공연 탐색':
    st.header('공연 탐색')
    catalog=catalog_loader()
    if not catalog.empty:
        f1,f2=st.columns([2,1]); kw=f1.text_input('공연명·장소 검색'); genre=f2.selectbox('장르',['전체']+sorted(catalog.genre.unique().tolist()))
        filtered=catalog[(catalog.title.str.contains(kw,case=False,regex=False)|catalog.venue.str.contains(kw,case=False,regex=False)) & ((catalog.genre==genre) if genre!='전체' else True)]
        st.caption(f'공연 {filtered.performance_id.nunique()}개 · 예매처 정보 {len(filtered)}건')
        view=st.radio('보기',['카드형','표형'],horizontal=True,label_visibility='collapsed')
        if view=='표형':
            st.dataframe(filtered[['title','venue','period','genre','vendor','url']].rename(columns={'title':'공연명','venue':'공연장','period':'공연기간','genre':'장르','vendor':'예매처','url':'예매처 링크'}),column_config={'예매처 링크':st.column_config.LinkColumn('예매처 링크')},hide_index=True,use_container_width=True)
        else:
            for _,group in filtered.groupby('performance_id',sort=False):
                r=group.iloc[0]
                with st.container(border=True):
                    pic,info=st.columns([1,4])
                    with pic:
                        if web_url(r.poster): st.image(r.poster,use_container_width=True)
                        else: st.caption('🎭 공연 포스터 없음')
                    with info:
                        st.caption(r.genre); st.subheader(r.title); st.write(r.venue+' · '+r.period)
                        for vendor in group.itertuples():
                            if web_url(vendor.url): st.link_button(vendor.vendor+' 바로가기 · '+r.performance_id,vendor.url)
                            else: st.caption(vendor.vendor+' · 링크 없음')
        if not filtered.empty:
            st.subheader('예매 일정 등록'); register_form(filtered,today,'discover')
    else: st.info('KOPIS 공연을 조회하면 포스터와 예매처 링크가 표시됩니다. 설정 전에는 시연 모드를 이용하세요.')

elif page=='예매 달력':
    st.header('예매 달력'); st.caption('달력의 날짜를 눌러 등록된 일정을 조회하고 해당 날짜에 새 일정을 추가하세요.')
    y,m=st.columns(2); year=y.selectbox('연도',list(range(today.year-2,today.year+6)),index=2); month=m.selectbox('월',list(range(1,13)),index=today.month-1,format_func=lambda x:f'{x}월')
    counts=day_counts(rows)
    if s.selected_day and (s.selected_day.year,s.selected_day.month)!=(year,month): s.selected_day=None
    headers=st.columns(7)
    for c,label in zip(headers,'일월화수목금토'): c.markdown('**'+label+'**')
    for week_days in month_grid(year,month):
        for col,day in zip(st.columns(7),week_days):
            if day:
                d=date(year,month,day); label=str(day)+(f' · {counts[d]}건' if counts[d] else '')
                if col.button(label,key=f'cal_{d}',type='primary' if d==s.selected_day else 'secondary',use_container_width=True): s.selected_day=d; st.rerun()
            else: col.write(' ')
    selected=s.selected_day
    if selected:
        st.subheader(selected.strftime('%Y년 %m월 %d일')+' 일정')
        selected_rows=filter_rows(rows,selected=selected)
        if not selected_rows: st.caption('등록된 일정이 없습니다.')
        for r in selected_rows:
            with st.container(border=True):
                st.write(f"**{r['title']}** · {local_dt(r['opening_at']).strftime('%H:%M')} · {r['status']}")
                if web_url(r['vendor_url']): st.link_button(r['vendor']+' · '+r['title']+' '+local_dt(r['opening_at']).strftime('%H:%M')+' · '+r['id'][:6],r['vendor_url'])
        st.subheader('선택 날짜에 예매 일정 등록')
        register_form(catalog,selected,'calreg_'+selected.isoformat())
    else: st.info('위 달력에서 날짜를 선택해 주세요.')

else:
    st.header('내 티켓')
    st.caption('예매 예정과 구매 완료 여부를 관리합니다. 이 기록은 실제 입장권이 아닙니다.')
    if not can_save: st.info('로그인하거나 시연 모드를 켜서 내 티켓을 이용하세요.')
    if not rows: st.info('저장된 일정이 없습니다. 공연 탐색 또는 예매 달력에서 추가해 주세요.')
    else:
        q1,q2,q3=st.columns([2,1,1]); kw=q1.text_input('내 티켓 검색'); vendor=q2.selectbox('예매처',['전체']+sorted(set(r['vendor'] for r in rows))); status=q3.selectbox('상태',['전체']+STATUSES)
        hide=st.checkbox('지난 오픈 일정 숨기기'); filtered=filter_rows(rows,keyword=kw,vendor=vendor,hide_past=hide,now=now); filtered=[r for r in filtered if status=='전체' or r['status']==status]
        display_view=st.radio('보기',['카드형','표형'],horizontal=True,label_visibility='collapsed')
        if display_view=='표형' and filtered:
            frame=pd.DataFrame([{'공연명':r['title'],'예매처':r['vendor'],'오픈 일시':local_dt(r['opening_at']).strftime('%Y-%m-%d %H:%M'),'상태':r['status'],'메모':r['note']} for r in filtered]); st.dataframe(frame,hide_index=True,use_container_width=True); st.download_button('내 일정 CSV 다운로드',frame.to_csv(index=False).encode('utf-8-sig'),'my_tickets.csv','text/csv')
        if not filtered: st.caption('필터 조건에 맞는 일정이 없습니다.')
        for r in filtered:
            rid=r['id']; dt=local_dt(r['opening_at'])
            with st.container(border=True):
                st.caption(dday(r['opening_at'],now)+' · '+r['status']); st.subheader(r['title']); st.write(dt.strftime('%Y-%m-%d %H:%M')+' KST · '+r['vendor']+' · '+r['venue']); st.caption(r['note'] or '메모 없음')
                if web_url(r['vendor_url']): st.link_button('공식 예매처 바로가기 · '+r['title']+' '+dt.strftime('%m/%d %H:%M')+' · '+rid[:6],r['vendor_url'])
                with st.expander('일정 수정 및 구매 상태 변경'):
                    with st.form('edit_'+rid):
                        d=st.date_input('오픈 날짜',dt.date()); t=st.time_input('오픈 시간',dt.time()); state=st.selectbox('상태',STATUSES,index=STATUSES.index(r['status'])); note=st.text_input('메모',r['note'],max_chars=500); submitted=st.form_submit_button('변경사항 저장')
                    if submitted:
                        try: modify(rid,{'opening_at':datetime.combine(d,t,KST).isoformat(),'status':state,'note':note}); s.flash='일정을 수정했습니다.'; st.rerun()
                        except ValueError: st.error('동일한 일정이 이미 존재합니다.')
                        except Exception as exc: st.error(db.error_message(exc))
                    if st.checkbox('이 일정을 삭제하겠습니다.',key='confirm_'+rid):
                        if st.button('삭제',key='del_'+rid):
                            try: remove(rid); s.flash='일정을 삭제했습니다.'; st.rerun()
                            except Exception as exc: st.error(db.error_message(exc))
