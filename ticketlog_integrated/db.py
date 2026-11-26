"""Supabase 계정별 저장. 클라이언트를 사용자 세션마다 분리한다."""
TABLE='ticketlog_schedules'

def create_session_client(url,key):
    from supabase import create_client
    return create_client(url,key)

def list_tickets(client, uid):
    return client.table(TABLE).select('*').eq('user_id',uid).order('opening_at').execute().data or []

def add_ticket(client, uid, data):
    return client.table(TABLE).insert(dict(data,user_id=uid)).execute()

def update_ticket(client, uid, rid, changes):
    return client.table(TABLE).update(changes).eq('id',rid).eq('user_id',uid).execute()

def delete_ticket(client,uid,rid):
    return client.table(TABLE).delete().eq('id',rid).eq('user_id',uid).execute()

def error_message(exc):
    # 비밀번호/토큰/내부 주소가 노출되지 않도록 오류 코드별 안내만 출력한다.
    code=str(getattr(exc,'code','') or '').lower()
    msg=str(getattr(exc,'message','') or '').lower()
    s=code+' '+msg
    if 'weak_password' in s or 'password should' in s or 'password is too' in s or 'password must' in s: return '비밀번호가 서버 보안 조건에 맞지 않습니다. 8자 이상, 대·소문자, 숫자, 특수문자를 조합해 주세요.'
    if 'email_not_confirmed' in s or 'email not confirmed' in s: return '이메일 인증을 완료한 뒤 로그인해 주세요.'
    if 'user_already_exists' in s or 'already registered' in s: return '이미 가입된 이메일입니다. 로그인해 주세요.'
    if 'invalid_credentials' in s or 'invalid login credentials' in s: return '이메일 또는 비밀번호를 확인해 주세요.'
    if 'rate_limit' in s or 'rate limit' in s: return '요청 제한에 도달했습니다. 잠시 후 다시 시도해 주세요.'
    if 'signup_disabled' in s: return '서버의 신규 회원가입이 비활성화되어 있습니다.'
    if 'email_address_invalid' in s: return '이메일 주소를 확인해 주세요.'
    if '23505' in s or 'duplicate key' in s: return '같은 공연·예매처·오픈 시간의 일정이 이미 있습니다.'
    if 'pgrst205' in s or '42p01' in s: return '데이터베이스 테이블이 없습니다. schema.sql을 먼저 실행해 주세요.'
    return '요청을 처리하지 못했습니다. 연결 설정과 입력 내용을 확인해 주세요.'
