import json
import os
import tempfile
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from trading_bot.live_web import DashboardApp
from trading_bot.kite.session import KiteSessionStore, execution_token
from trading_bot.kite.execution import KiteMonitorClient
from trading_bot.kite.client import KiteForbiddenEndpoint
from trading_bot.live_store import LiveStore, LiveHalt
from test_live import NOW, Broker


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.clock = NOW
        self.calls = []
        def exchange(key, secret, request):
            self.calls.append(request)
            return {'user_id':'AB1234', 'access_token':'server-secret-token'}
        self.broker = Broker()
        self.broker.cash_snapshot=lambda: dict(account_cash_inr=self.broker.cash,usable_cash_inr=self.broker.cash)
        self.app = DashboardApp(self.root, 'https://dashboard.example', 'a-private-password-long',
            account_id='AB1234', api_key='key', api_secret='server-secret',
            exchange=exchange, broker_factory=lambda *args: self.broker, clock=lambda:self.clock)
        self.app.schedule_refresh = lambda: None
        self.headers = {'Host':'dashboard.example', 'Origin':'https://dashboard.example'}
    def request(self, method, path, data=None, headers=None):
        return self.app.handle(method, path, headers or self.headers,
            urlencode(data or {}).encode(), '127.0.0.1')
    def login(self):
        status, headers, body = self.request('POST','/login',{'password':'a-private-password-long'})
        self.assertEqual(status,303)
        self.headers['Cookie'] = headers['Set-Cookie'].split(';')[0]
        session_id = self.headers['Cookie'].split('=')[1]
        return self.app.sessions[session_id]['csrf']
    def test_private_state_requires_login_and_host_is_checked(self):
        self.assertEqual(self.request('GET','/api/state')[0],401)
        self.assertEqual(self.request('GET','/',headers={'Host':'evil.example'})[0],400)
        self.assertEqual(self.request('POST','/login',{'password':'wrong'})[0],401)
    def test_secure_cookie_headers_and_token_secrecy(self):
        csrf = self.login()
        status, headers, body = self.request('GET','/')
        self.assertEqual(status,200)
        self.assertIn('no-store',headers['Cache-Control'])
        self.assertIn("form-action 'self' https://kite.zerodha.com",headers['Content-Security-Policy'])
        self.assertNotIn(b'server-secret',body)
        self.assertIn(csrf.encode(),body)
    def test_csrf_and_origin_required_for_mutations(self):
        csrf = self.login()
        self.assertEqual(self.request('POST','/pause',{})[0],403)
        self.assertEqual(self.request('POST','/pause',{'csrf':csrf},dict(self.headers,Origin='null'))[0],403)
        self.assertEqual(self.request('POST','/login',{'password':'a-private-password-long'},dict(self.headers,Origin='null'))[0],403)
        self.assertEqual(self.request('POST','/pause',{'csrf':csrf}, dict(self.headers,Origin='https://evil.example'))[0],403)
        self.assertFalse((self.root/'PAUSE').exists())
        self.assertEqual(self.request('POST','/pause',{'csrf':csrf})[0],200)
        self.assertTrue((self.root/'PAUSE').exists())
        self.assertFalse((self.root/'STOP').exists())
    def test_pause_resume_is_authenticated_idempotent_and_does_not_call_broker(self):
        self.assertEqual(self.request('POST','/resume')[0],303)
        csrf=self.login()
        self.request('POST','/pause',{'csrf':csrf})
        self.assertEqual(self.request('POST','/resume',{})[0],403)
        self.assertTrue((self.root/'PAUSE').exists())
        self.assertEqual(self.request('POST','/resume',{'csrf':csrf},dict(self.headers,Origin='null'))[0],403)
        for _ in range(2):
            self.assertEqual(self.request('POST','/resume',{'csrf':csrf})[0],200)
        self.assertFalse((self.root/'PAUSE').exists())
        self.assertFalse(self.app.snapshot()['paused'])
        self.assertEqual(self.broker.calls,[])
        self.assertEqual(self.app.snapshot()['runner']['status'],'NOT_RUNNING')

    def test_pause_resume_invalidates_pending_agent_work_and_old_inbox(self):
        from trading_bot.autopilot import agent_work_is_current
        from trading_bot.live import LiveRunner
        from trading_bot.live_engine import LiveConfig, LiveEngine
        from test_live import decision
        csrf=self.login()
        captured_revision=self.app.store.entry_pause_revision()
        inbox=self.root/'inbox'
        inbox.mkdir()
        payload=decision()
        payload['entry_pause_revision']=captured_revision
        queued=inbox/'old.json'
        queued.write_text(json.dumps(payload))
        self.clock += timedelta(seconds=1)
        self.request('POST','/pause',{'csrf':csrf})
        self.clock += timedelta(seconds=1)
        self.request('POST','/resume',{'csrf':csrf})
        self.assertFalse(agent_work_is_current(self.app.store,captured_revision))
        self.assertTrue(agent_work_is_current(self.app.store,self.app.store.entry_pause_revision()))
        engine=LiveEngine(self.app.store,self.broker,LiveConfig('AB1234',1000,10000,2000,1,200))
        runner=LiveRunner(engine,object(),self.root,log=lambda _:None,clock=lambda:self.clock)
        runner.ingest(self.clock)
        self.assertFalse(queued.exists())
        self.assertTrue((inbox/'processed'/'old.json').exists())
        self.assertEqual(self.broker.calls,[])
        self.assertEqual(self.app.store.all(),[])
        # Legacy/manual queued decisions are checked by their decision time.
        payload.pop('entry_pause_revision')
        (inbox/'legacy.json').write_text(json.dumps(payload))
        runner.ingest(self.clock)
        self.assertTrue((inbox/'processed'/'legacy.json').exists())
        self.assertEqual(self.broker.calls,[])

    def test_concurrent_pause_resume_are_serialized(self):
        csrf=self.login()
        pause_writing=threading.Event()
        release_pause=threading.Event()
        resume_attempt=threading.Event()
        blocked=[]
        replies={}
        writes=[]
        class ObservedLock:
            def __init__(self): self.lock=threading.RLock()
            def __enter__(self):
                acquired=self.lock.acquire(blocking=False)
                if threading.current_thread().name=='resume-request':
                    blocked.append(not acquired)
                    resume_attempt.set()
                if not acquired: self.lock.acquire()
            def __exit__(self,*args): self.lock.release()
        self.app.lock=ObservedLock()
        original=self.app.store.set_metadata
        def metadata(key,value):
            if key=='entry_pause':
                if threading.current_thread().name=='pause-request':
                    pause_writing.set()
                    if not release_pause.wait(2): raise RuntimeError('test timed out')
                writes.append(threading.current_thread().name)
            return original(key,value)
        self.app.store.set_metadata=metadata
        def control(action):
            replies[action]=self.request('POST','/'+action,{'csrf':csrf})[0]
        pause=threading.Thread(name='pause-request',target=control,args=('pause',))
        resume=threading.Thread(name='resume-request',target=control,args=('resume',))
        pause.start()
        try:
            self.assertTrue(pause_writing.wait(2))
            resume.start()
            self.assertTrue(resume_attempt.wait(2))
            self.assertTrue(blocked[0])
        finally:
            release_pause.set()
            pause.join(2)
            if resume.ident: resume.join(2)
        self.assertEqual(replies,{'pause':200,'resume':200})
        self.assertEqual(writes,['pause-request','resume-request'])
        self.assertFalse((self.root/'PAUSE').exists())

    def test_resume_cannot_clear_stop_or_trade_halt(self):
        csrf=self.login()
        self.request('POST','/pause',{'csrf':csrf})
        (self.root/'STOP').touch()
        self.assertEqual(self.request('POST','/resume',{'csrf':csrf})[0],409)
        self.assertTrue((self.root/'PAUSE').exists())
        self.assertTrue((self.root/'STOP').exists())
        (self.root/'STOP').unlink()
        from trading_bot.live_engine import LiveConfig, LiveEngine
        from test_live import decision
        engine=LiveEngine(self.app.store,self.broker,LiveConfig('AB1234',1000,10000,2000,1,200))
        engine.accept(decision(),NOW)
        trade=self.app.store.all()[0]
        trade['halted']=True
        self.app.store.save(trade)
        calls=list(self.broker.calls)
        self.assertEqual(self.request('POST','/resume',{'csrf':csrf})[0],409)
        self.assertTrue((self.root/'PAUSE').exists())
        self.assertTrue(self.app.store.all()[0]['halted'])
        self.assertEqual(self.broker.calls,calls)
        self.assertTrue(self.app.snapshot()['resume_block_reason'])

    def start_kite(self):
        csrf = self.login()
        status, headers, body = self.request('POST','/kite/login',{'csrf':csrf})
        self.assertEqual(status,303)
        url = urlsplit(headers['Location'])
        self.assertEqual(url.netloc,'kite.zerodha.com')
        return parse_qs(parse_qs(url.query)['redirect_params'][0])['state'][0]
    def test_official_callback_bound_to_session_and_single_use(self):
        state = self.start_kite()
        path = '/kite/callback?'+urlencode(dict(state=state,request_token='request-secret',status='success'))
        self.assertEqual(self.request('GET',path,headers={'Host':'dashboard.example'})[0],403)
        self.assertEqual(self.request('GET',path)[0],303)
        self.assertEqual(self.request('GET',path)[0],403)
        self.assertEqual(self.calls,['request-secret'])
        token_file = self.root/'kite-session.json'
        self.assertEqual(token_file.stat().st_mode & 0o777,0o600)
        self.assertEqual(execution_token(self.root, 'AB1234', NOW, fallback='old'), 'server-secret-token')
        self.app.refresh_broker()
        body = self.request('GET','/api/state')[2]
        self.assertNotIn(b'server-secret-token',body)
        self.assertNotIn(b'request-secret',body)
        self.assertNotIn(b'server-secret',body)
    def test_local_root_callback_retains_state_and_session_checks(self):
        self.app=DashboardApp(self.root,'http://127.0.0.1:8080','a-private-password-long',
            account_id='AB1234',api_key='key',api_secret='secret',exchange=self.app.exchange,
            broker_factory=lambda *args:self.broker,clock=lambda:self.clock,allow_local_http=True)
        self.headers={'Host':'127.0.0.1:8080','Origin':'http://127.0.0.1:8080'}
        state=self.start_kite()
        path='/?'+urlencode(dict(state=state,request_token='local-request',status='success'))
        self.assertEqual(self.request('GET',path,headers={'Host':'127.0.0.1:8080'})[0],403)
        self.assertEqual(self.request('GET',path)[0],303)
        self.assertEqual(self.request('GET',path)[0],403)
        self.assertEqual(self.calls,['local-request'])

    def test_expired_state_and_wrong_account_do_not_save_token(self):
        state = self.start_kite()
        self.clock += timedelta(minutes=11)
        self.assertEqual(self.request('GET','/kite/callback?'+urlencode(dict(state=state,request_token='r',status='success')))[0],403)
        self.assertEqual(self.calls,[])
        self.clock = NOW
        state = self.start_kite()
        self.broker.user_id = 'OTHER'
        self.assertEqual(self.request('GET','/kite/callback?'+urlencode(dict(state=state,request_token='r',status='success')))[0],400)
        self.assertFalse((self.root/'kite-session.json').exists())
    def test_duplicate_callback_parameters_fail_closed(self):
        state = self.start_kite()
        path = '/kite/callback?state='+state+'&state=wrong&request_token=r&status=success'
        self.assertEqual(self.request('GET',path)[0],403)
        self.assertEqual(self.calls,[])
    def test_connection_expiry_unknown_budget_and_failed_refresh(self):
        self.login()
        state = json.loads(self.request('GET','/api/state')[2])
        self.assertIsNone(state['capital']['available_for_new_trade_inr'])
        self.assertNotEqual(state['connection']['status'],'CONNECTED')
        self.assertEqual(state['capital']['allocation_inr'],10000)
    def test_logout_and_session_expiry(self):
        csrf = self.login()
        self.assertEqual(self.request('POST','/logout',{'csrf':csrf})[0],303)
        self.assertEqual(self.request('GET','/api/state')[0],401)
    def test_public_url_requires_https_except_explicit_loopback(self):
        with self.assertRaises(ValueError):
            DashboardApp(self.root, 'http://dashboard.example', 'a-private-password-long')
        with self.assertRaises(ValueError):
            DashboardApp(self.root,'https://dashboard.example/path','a-private-password-long')
    def test_persisted_realized_budget_and_cash_ceiling(self):
        from trading_bot.live_engine import LiveConfig, LiveEngine
        from test_live import decision
        engine=LiveEngine(self.app.store,self.broker,LiveConfig('AB1234',1000,10000,2000,1,200))
        engine.accept(decision(),NOW); self.broker.fill(0,65); engine.step(NOW,bid=100); engine.step(NOW,bid=100)
        self.broker.fill(1,65,price=120); engine.step(NOW,bid=100)
        self.app.tokens.save('private-token','AB1234',NOW)
        self.broker.cash=9000
        self.app.refresh_broker()
        state=self.app.snapshot()
        self.assertEqual(state['capital']['allocation_inr'],11240)
        self.assertEqual(state['capital']['available_for_new_trade_inr'],9000)
        self.assertEqual(state['daily_pnl'],1240)
        self.assertEqual(state['completed'][0]['net_pnl'],1240)
        self.clock += timedelta(seconds=31)
        self.assertIsNone(self.app.snapshot()['capital']['available_for_new_trade_inr'])
    def test_zerodha_account_cash_is_distinct_from_bot_cash_and_ages_out(self):
        self.app.tokens.save('private-token','AB1234',NOW)
        self.broker.cash_snapshot=lambda: dict(account_cash_inr=42000,usable_cash_inr=9000)
        self.app.refresh_broker()
        state=self.app.snapshot()
        self.assertEqual(state['account_cash_inr'],42000)
        self.assertEqual(state['capital']['broker_cash_inr'],9000)
        self.assertEqual(state['capital']['allocation_inr'],10000)
        self.clock+=timedelta(seconds=31)
        self.assertIsNone(self.app.snapshot()['account_cash_inr'])

    def test_pause_blocks_existing_inbox_without_broker_calls(self):
        from trading_bot.live import LiveRunner
        from trading_bot.live_engine import LiveConfig, LiveEngine
        engine=LiveEngine(self.app.store,self.broker,LiveConfig('AB1234',1000,10000,2000,1,200))
        (self.root/'PAUSE').touch()
        runner=LiveRunner(engine,object(),self.root,clock=lambda:NOW)
        runner.ingest(NOW)
        self.assertEqual(self.broker.calls,[])
        self.assertFalse((self.root/'inbox').exists())

    def test_runner_adopts_new_web_token_without_restart(self):
        from trading_bot.live import LiveRunner
        from trading_bot.live_engine import LiveConfig, LiveEngine
        from trading_bot.kite.execution import KiteExecutionClient
        responses={'/user/profile':{'user_id':'AB1234'},'/orders':[], '/portfolio/positions':{'net':[]}}
        calls=[]
        def transport(method,url,headers,body,timeout):
            calls.append(headers['Authorization'])
            return json.dumps({'status':'success','data':responses[urlsplit(url).path]}).encode()
        broker=KiteExecutionClient('key','old',enabled=True,transport=transport)
        engine=LiveEngine(self.app.store,broker,LiveConfig('AB1234',1000,10000,2000,1,200))
        self.app.tokens.save('fresh','AB1234',NOW)
        runner=LiveRunner(engine,object(),self.root,clock=lambda:NOW)
        runner.tick(NOW)
        self.assertTrue(all(value=='token key:fresh' for value in calls))
        self.assertEqual(self.app.store.metadata('runner_heartbeat')['status'],'RUNNING')

    def test_slow_broker_refresh_does_not_relabel_old_cash_as_fresh(self):
        self.app.tokens.save('token','AB1234',NOW)
        original_positions=self.broker.positions
        def slow_positions():
            self.clock += timedelta(seconds=31)
            return original_positions()
        self.broker.positions=slow_positions
        self.app.refresh_broker()
        self.assertEqual(self.app.snapshot()['connection']['status'],'STALE')
        self.assertIsNone(self.app.snapshot()['capital']['available_for_new_trade_inr'])

    def test_old_refresh_cannot_publish_under_new_login(self):
        original=self.app.tokens.save('old','AB1234',NOW)
        original_positions=self.broker.positions
        def replacement_login():
            new_session=self.app.tokens.save('new','AB1234',NOW)
            self.app.store.set_metadata('dashboard_broker',dict(status='CONNECTED',verified_at=NOW.isoformat(),generation=new_session['generation'],cash=None,positions=[],orders=[]))
            return original_positions()
        self.broker.positions=replacement_login
        self.app.refresh_broker()
        metadata=self.app.store.metadata('dashboard_broker')
        self.assertNotEqual(metadata['generation'],original['generation'])
        self.assertIsNone(metadata['cash'])
        self.assertIsNone(self.app.snapshot()['capital']['available_for_new_trade_inr'])

    def test_old_cached_cash_is_unavailable_after_token_replacement(self):
        self.app.tokens.save('old','AB1234',NOW)
        self.app.refresh_broker()
        self.assertIsNotNone(self.app.snapshot()['capital']['available_for_new_trade_inr'])
        self.app.tokens.save('new','AB1234',NOW)
        self.assertIsNone(self.app.snapshot()['capital']['available_for_new_trade_inr'])

    def test_overlapping_callbacks_serialize_token_exchange_and_publication(self):
        first_state=self.start_kite()
        first_headers=dict(self.headers)
        second_state=self.start_kite()
        second_headers=dict(self.headers)
        first_exchange=threading.Event()
        second_attempt=threading.Event()
        release_first=threading.Event()
        exchanged=[]
        replies=[]
        class ObservedLock:
            def __init__(self): self.lock=threading.Lock()
            def __enter__(self):
                if threading.current_thread().name=='second-login': second_attempt.set()
                self.lock.acquire()
            def __exit__(self,*args): self.lock.release()
        self.app.callback_lock=ObservedLock()
        def exchange(key,secret,request):
            exchanged.append(request)
            if request=='first':
                first_exchange.set()
                if not release_first.wait(2): raise RuntimeError('test timed out')
            return dict(user_id='AB1234',access_token=request)
        self.app.exchange=exchange
        def callback(state,request,headers):
            replies.append(self.request('GET','/kite/callback?'+urlencode(dict(state=state,request_token=request,status='success')),headers=headers)[0])
        first=threading.Thread(target=callback,args=(first_state,'first',first_headers))
        second=threading.Thread(name='second-login',target=callback,args=(second_state,'second',second_headers))
        first.start()
        try:
            self.assertTrue(first_exchange.wait(2))
            second.start()
            self.assertTrue(second_attempt.wait(2))
            self.assertEqual(exchanged,['first'])
        finally:
            release_first.set()
            first.join(2)
            if second.ident: second.join(2)
        self.assertEqual(replies,[303,303])
        self.assertEqual(exchanged,['first','second'])
        self.assertEqual(self.app.tokens.load(NOW,'AB1234')['access_token'],'second')

    def test_password_attempts_are_bounded(self):
        for _ in range(5): self.request('POST','/login',{'password':'wrong'})
        self.assertEqual(self.request('POST','/login',{'password':'wrong'})[0],429)


class SessionTests(unittest.TestCase):
    def test_local_dashboard_can_start_before_daily_login(self):
        from unittest.mock import patch
        from trading_bot.live_web import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root/'config.json'
            config.write_text(json.dumps(dict(account_id='AB1234',capital_limit_inr=10000,fee_reserve_inr=200)))
            KiteSessionStore(root/'kite-session.json').save('expired-token','AB1234',NOW)
            with patch.dict(os.environ,dict(DASHBOARD_PASSWORD='a-private-password-long',KITE_API_KEY='key',KITE_API_SECRET='secret')), \
                 patch('trading_bot.live_web.load_env_file'), patch('trading_bot.live_web.serve') as serve:
                self.assertIsNone(main(['--local','--root',str(root),'--config',str(config)]))
                app=serve.call_args.args[0]
                self.assertEqual(app.public_url,'http://127.0.0.1:8080')
                self.assertEqual(app.handle('GET','/login',{'Host':'127.0.0.1:8080'})[0],200)

    def test_expiry_account_binding_and_env_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(execution_token(root,'AB1234',NOW,fallback='env-token'),'env-token')
            store = KiteSessionStore(root/'kite-session.json')
            store.save('token','AB1234',NOW)
            self.assertEqual(store.load(NOW,'AB1234')['access_token'],'token')
            with self.assertRaises(LiveHalt): store.load(NOW,'OTHER')
            with self.assertRaises(LiveHalt): execution_token(root,'AB1234',NOW+timedelta(days=1),fallback='env-token')
    def test_monitor_client_can_never_mutate_orders(self):
        client = KiteMonitorClient('key','token',transport=lambda *args:self.fail('transport called'))
        with self.assertRaises(KiteForbiddenEndpoint): client._call('POST','/orders/regular',{})
        with self.assertRaises(KiteForbiddenEndpoint): client._call('DELETE','/orders/regular/1')
