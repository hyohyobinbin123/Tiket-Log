from datetime import date,datetime,timedelta
from unittest.mock import patch
import unittest
import catalog, schedule, db

class CoreTests(unittest.TestCase):
    def test_calendar_sunday_first(self):
        self.assertEqual(schedule.month_grid(2026,11)[0],[1,2,3,4,5,6,7])
    def test_leap_year(self):
        self.assertEqual(sum(x>0 for week in schedule.month_grid(2028,2) for x in week),29)
    def test_timezone(self):
        self.assertEqual(schedule.local_dt('2026-11-26T15:00:00Z').date(),date(2026,11,27))
    def test_dday(self):
        n=datetime(2026,11,26,10,tzinfo=schedule.KST)
        self.assertEqual(schedule.dday('2026-11-27T14:00:00+09:00',n),'D-1')
        self.assertEqual(schedule.dday('2026-11-26T09:00:00+09:00',n),'오픈 지남')
        self.assertEqual(schedule.dday('2026-11-26T11:00:00+09:00',n),'D-Day')
    def test_filter_counts(self):
        rows=[dict(title='달빛 뮤지컬',venue='서울',vendor='예매처',genre='뮤지컬',opening_at='2026-11-26T15:00:00+09:00',status='예매 예정'),dict(title='콘서트',venue='부산',vendor='다른곳',genre='대중음악',opening_at='2026-11-27T15:00:00+09:00',status='구매 완료')]
        n=datetime(2026,11,26,10,tzinfo=schedule.KST)
        self.assertEqual(len(schedule.upcoming(rows,n)),1)
        self.assertEqual(len(schedule.filter_rows(rows,keyword='달빛',selected=date(2026,11,26))),1)
        self.assertEqual(schedule.day_counts(rows)[date(2026,11,27)],1)
        self.assertEqual(len(schedule.filter_rows(rows,genre='대중음악')),1)
    def test_demo_separate(self):
        d=catalog.demo_catalog(date(2026,11,26))
        self.assertEqual(len(d),4); self.assertTrue(d.demo.all()); self.assertTrue(d.title.str.startswith('[시연]').all()); self.assertTrue((d.url=='').all())
    def test_url(self):
        self.assertEqual(catalog.web_url('javascript:alert(1)'),'')
        self.assertEqual(catalog.web_url('https://example.com/a'),'https://example.com/a')
    def test_mock_kopis_multiple_vendors(self):
        items=catalog.parse_rows(b'<dbs><db><mt20id>PF123</mt20id></db></dbs>')
        detail=catalog.parse_rows('''<dbs><db><prfnm>공연</prfnm><fcltynm>극장</fcltynm><relates><relate><relatenm>A</relatenm><relateurl>https://example.com/a</relateurl></relate><relate><relatenm>B</relatenm><relateurl>https://example.com/b</relateurl></relate></relates></db></dbs>''')
        with patch('catalog.get_xml',side_effect=[items,detail]):
            df,failures=catalog.fetch_kopis_data('test',date(2026,11,26),date(2026,12,1))
        self.assertEqual(list(df.vendor),['A','B']); self.assertEqual(failures,0); self.assertFalse(df.demo.any())
    def test_mock_no_vendors(self):
        items=catalog.parse_rows(b'<dbs><db><mt20id>PF123</mt20id></db></dbs>')
        detail=catalog.parse_rows(b'<dbs><db><prfnm>test</prfnm></db></dbs>')
        with patch('catalog.get_xml',side_effect=[items,detail]):
            df,failures=catalog.fetch_kopis_data('test',date(2026,11,26),date(2026,12,1))
        self.assertEqual(df.iloc[0].vendor,'미등록')
    def test_bad_xml(self):
        with self.assertRaises(ValueError): catalog.parse_rows(b'<error/>')
    def test_auth_error(self):
        e=type('Error',(),{'code':'weak_password','message':'secret'})()
        self.assertIn('비밀번호',db.error_message(e)); self.assertNotIn('secret',db.error_message(e))
    def test_range_validation(self):
        with self.assertRaises(ValueError): catalog.fetch_kopis_data('test',date(2026,1,1),date(2026,12,31))

if __name__=='__main__': unittest.main()
