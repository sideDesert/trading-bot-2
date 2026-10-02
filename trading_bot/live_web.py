"""Private mobile dashboard and official Kite callback. No order placement routes."""
import argparse
import hashlib
import hmac
import html
import json
import math
import os
import secrets
import threading
import time
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from .config import load_env_file
from .features import IST
from .kite.execution import KiteMonitorClient
from .kite.login import exchange_token, login_url
from .kite.session import KiteSessionStore
from .live import LIVE_ROOT
from .live_store import LiveStore, LiveHalt
from .live_budget import capital_from_trades

ASSETS = Path(__file__).parent/'web_assets'
COOKIE = 'trading_dashboard'




class DashboardApp:
    def __init__(self, root, public_url, password, *, account_id=None, api_key='', api_secret='',
                 starting_capital=10000, fee_reserve=200, exchange=exchange_token,
                 broker_factory=KiteMonitorClient, clock=lambda:datetime.now(IST), allow_local_http=False, demo=False):
        address = urlsplit(public_url)
        local = address.hostname in ('127.0.0.1','localhost','::1')
        if (address.scheme!='https' and not (allow_local_http and local and address.scheme=='http')) or (
                not address.netloc or address.path not in ('','/') or address.query or address.fragment or address.username):
            raise ValueError('Dashboard public URL must be an HTTPS origin; HTTP is loopback-only with explicit opt-in')
        if not isinstance(password,str) or len(password)<16:
            raise ValueError('Private dashboard password must contain at least 16 characters')
        self.root, self.public_url, self.host = Path(root), public_url.rstrip('/'), address.netloc
        self.secure_cookie = address.scheme=='https'
        self.account_id, self.api_key, self.api_secret = account_id, api_key, api_secret
        self.starting, self.fee_reserve, self.exchange = starting_capital, fee_reserve, exchange
        self.broker_factory, self.clock, self.demo = broker_factory, clock, demo
        self.store = LiveStore(self.root/'state.sqlite3') if not demo else None
        if self.store:
            bound_account = self.store.metadata('account')
            bound_capital = self.store.metadata('starting_capital')
            if bound_account and bound_account != account_id:
                raise ValueError('Dashboard account differs from execution journal')
            if bound_capital is not None and bound_capital != starting_capital:
                raise ValueError('Dashboard starting allocation differs from execution journal')
        if not math.isfinite(starting_capital) or starting_capital <= 0 or not math.isfinite(fee_reserve) or fee_reserve < 200:
            raise ValueError('Invalid capital configuration')
        self.tokens = KiteSessionStore(self.root/'kite-session.json')
        self.salt = secrets.token_bytes(16)
        self.password_hash = self._password_hash(password)
        self.sessions, self.attempts = {}, {}
        self.lock = threading.RLock()
        self.refresh_lock = threading.Lock()
        self.callback_lock = threading.Lock()
        self.last_refresh_attempt = float('-inf')

    def _password_hash(self, password):
        return hashlib.scrypt(password.encode(), salt=self.salt, n=16384, r=8, p=1)

    def _reply(self, status, body='', headers=None, content_type='text/html; charset=utf-8'):
        result = {'Content-Type':content_type, 'Cache-Control':'no-store', 'Referrer-Policy':'no-referrer',
            'X-Content-Type-Options':'nosniff', 'X-Frame-Options':'DENY',
            'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'self' https://kite.zerodha.com; frame-ancestors 'none'; base-uri 'none'"}
        if self.secure_cookie: result['Strict-Transport-Security']='max-age=31536000'
        result.update(headers or {})
        return status,result,body.encode() if isinstance(body,str) else body

    def _session(self, headers):
        try:
            cookies = SimpleCookie(headers.get('Cookie',''))
            session_id = cookies[COOKIE].value
            with self.lock:
                session = self.sessions.get(session_id)
                if session and session['expires']>self.clock(): return session_id,session
                self.sessions.pop(session_id,None)
        except (KeyError,ValueError): pass
        return None,None

    def _cookie(self, session_id, expired=False):
        return COOKIE+'='+session_id+'; Path=/; HttpOnly; SameSite=Lax; Max-Age='+('0' if expired else '43200')+('; Secure' if self.secure_cookie else '')

    def handle(self, method, path, headers, body=b'', remote='local'):
        if headers.get('Host')!=self.host: return self._reply(400,'Invalid host')
        target=urlsplit(path)
        if target.scheme or target.netloc or len(body)>4096: return self._reply(400,'Invalid request')
        if method not in ('GET','POST'): return self._reply(405,'Method not allowed')
        if method=='POST' and headers.get('Origin')!=self.public_url: return self._reply(403,'Invalid origin')
        if target.path in ('/static/dashboard.css','/static/dashboard.js') and method=='GET':
            asset=ASSETS/target.path.rsplit('/',1)[1]
            return self._reply(200,asset.read_bytes(),content_type='text/css' if asset.suffix=='.css' else 'text/javascript')
        if target.path=='/login' and method=='GET':
            return self._reply(200,(ASSETS/'login.html').read_text())
        form=parse_qs(body.decode(errors='replace'),keep_blank_values=True)
        if target.path=='/login' and method=='POST':
            with self.lock:
                attempts=[stamp for stamp in self.attempts.get(remote,[]) if time.monotonic()-stamp<60]
                if len(attempts)>=5: return self._reply(429,'Too many attempts. Try again in a minute.')
                attempts.append(time.monotonic()); self.attempts[remote]=attempts
            passwords=form.get('password',[])
            if len(passwords)!=1 or not hmac.compare_digest(self._password_hash(passwords[0]),self.password_hash):
                return self._reply(401,'Incorrect dashboard password. <a href="/login">Try again</a>')
            session_id=secrets.token_hex(32)
            with self.lock:
                self.sessions[session_id]=dict(csrf=secrets.token_hex(32),expires=self.clock()+timedelta(hours=12),oauth=None)
            return self._reply(303,headers={'Location':'/','Set-Cookie':self._cookie(session_id)})
        session_id,session=self._session(headers)
        if not session and not self.demo:
            if target.path=='/kite/callback': return self._reply(403,'Kite login requires the original dashboard session. Start again.')
            return self._reply(401,json.dumps({'error':'Dashboard sign-in required'}),content_type='application/json') if target.path=='/api/state' else self._reply(303,headers={'Location':'/login'})
        if self.demo: session={'csrf':'demo','oauth':None}
        if method=='POST':
            values=form.get('csrf',[])
            if len(values)!=1 or not hmac.compare_digest(values[0],session['csrf']): return self._reply(403,'Invalid request token')
            if self.demo: return self._reply(403,'Preview controls are disabled')
        if target.path=='/' and method=='GET':
            return self._reply(200,(ASSETS/'dashboard.html').read_text().replace('__CSRF__',html.escape(session['csrf'],quote=True)))
        if target.path=='/api/state' and method=='GET':
            self.schedule_refresh()
            return self._reply(200,json.dumps(self.snapshot(),allow_nan=False),content_type='application/json')
        if target.path=='/pause' and method=='POST':
            self.root.mkdir(parents=True,exist_ok=True)
            descriptor=os.open(self.root/'PAUSE',os.O_CREAT|os.O_WRONLY,0o600)
            os.close(descriptor)
            return self._reply(200,json.dumps({'paused':True}),content_type='application/json')
        if target.path=='/logout' and method=='POST':
            with self.lock: self.sessions.pop(session_id,None)
            return self._reply(303,headers={'Location':'/login','Set-Cookie':self._cookie('',True)})
        if target.path=='/kite/login' and method=='POST':
            if not self.account_id or not self.api_key or not self.api_secret: return self._reply(503,'Kite configuration is incomplete')
            with self.lock: session['oauth']=dict(state=secrets.token_hex(32),expires=self.clock()+timedelta(minutes=10))
            url=login_url(self.api_key)+'&'+urlencode({'redirect_params':urlencode({'state':session['oauth']['state']})})
            return self._reply(303,headers={'Location':url})
        if target.path=='/kite/callback' and method=='GET':
            query=parse_qs(target.query,keep_blank_values=True)
            with self.lock:
                pending=session.get('oauth')
                if (not pending or pending['expires']<=self.clock() or any(len(query.get(k,[]))!=1 for k in ('state','request_token','status')) or
                        query['status'][0]!='success' or not hmac.compare_digest(query['state'][0],pending['state'])):
                    return self._reply(403,'Invalid or expired Kite callback. Start login again.')
                session['oauth']=None # consume before exchange; a timeout requires a fresh login
            with self.callback_lock: # token exchanges must publish in issuance order
                try:
                    data=self.exchange(self.api_key,self.api_secret,query['request_token'][0])
                    broker=self.broker_factory(self.api_key,data['access_token'])
                    if data.get('user_id')!=self.account_id or broker.profile().get('user_id')!=self.account_id:
                        raise LiveHalt('Account mismatch')
                    with self.lock:
                        token_session=self.tokens.save(data['access_token'],self.account_id,self.clock())
                        self.store.set_metadata('dashboard_broker',dict(status='CONNECTED',verified_at=self.clock().isoformat(),generation=token_session['generation'],cash=None,positions=[],orders=[]))
                        self.last_refresh_attempt=float('-inf')
                    return self._reply(303,headers={'Location':'/'})
                except Exception:
                    return self._reply(400,'Kite login could not be verified. Return to the dashboard and start again.')
        return self._reply(404,'Not found')

    def schedule_refresh(self):
        if self.demo or not self.account_id or not self.api_key or time.monotonic()-self.last_refresh_attempt<15: return
        if self.refresh_lock.acquire(blocking=False):
            self.last_refresh_attempt=time.monotonic()
            def worker():
                try: self.refresh_broker()
                except Exception: pass # storage failure must not print private request context
                finally: self.refresh_lock.release()
            threading.Thread(target=worker,daemon=True).start()

    def refresh_broker(self):
        session=None
        try:
            checked_at=self.clock() # freshness begins before any broker reads
            session=self.tokens.load(checked_at,self.account_id)
            broker=self.broker_factory(self.api_key,session['access_token'])
            if broker.profile().get('user_id')!=self.account_id: raise LiveHalt('Account mismatch')
            cash=float(broker.cash_available())
            if not math.isfinite(cash): raise LiveHalt('Cash unavailable')
            fields=('order_id','tradingsymbol','exchange','transaction_type','quantity','filled_quantity','pending_quantity','status','order_type','price','trigger_price')
            orders=[{key:order.get(key) for key in fields} for order in broker.orders() if order.get('exchange')=='NFO' and order.get('status') not in ('COMPLETE','CANCELLED','REJECTED')]
            positions=[{key:position.get(key) for key in ('tradingsymbol','exchange','product','quantity','average_price','last_price','pnl')} for position in broker.positions() if position.get('exchange')=='NFO' and position.get('quantity')]
            with self.lock:
                current=self.tokens.load(self.clock(),self.account_id)
                if current.get('generation')!=session.get('generation'): return
                self.store.set_metadata('dashboard_broker',dict(status='CONNECTED',verified_at=checked_at.isoformat(),generation=session.get('generation'),cash=cash,positions=positions,orders=orders))
        except Exception:
            with self.lock:
                try:
                    current=self.tokens.load(self.clock(),self.account_id)
                    if session is None or current.get('generation')!=session.get('generation'): return
                except LiveHalt: pass
                previous=self.store.metadata('dashboard_broker') or {}
                previous.update(status='LOGIN_REQUIRED',cash=None)
                self.store.set_metadata('dashboard_broker',previous)

    def snapshot(self):
        if self.demo:
            return dict(demo=True,connection={'status':'DEMO','verified_at':None},capital={'allocation_inr':10000,'available_for_new_trade_inr':None,'realized_net_pnl_inr':0,'committed_inr':0,'broker_cash_inr':None},
                daily_pnl=0,paused=False,runner={'status':'NOT_RUNNING'},open_trades=[],completed=[],positions=[],orders=[],login_ready=False,generated_at=self.clock().isoformat())
        trades=self.store.all()
        broker=self.store.metadata('dashboard_broker') or dict(status='LOGIN_REQUIRED',cash=None,positions=[],orders=[])
        connection=dict(status=broker['status'],verified_at=broker.get('verified_at'))
        fresh=False
        try:
            token_session=self.tokens.load(self.clock(),self.account_id)
            verified=datetime.fromisoformat(broker['verified_at'])
            fresh=broker['status']=='CONNECTED' and broker.get('generation')==token_session.get('generation') and 0<=(self.clock()-verified).total_seconds()<=30
            if not fresh: connection['status']='STALE'
        except Exception: connection['status']='LOGIN_REQUIRED'
        try:
            capital=capital_from_trades(trades,self.starting,self.fee_reserve,broker.get('cash') if fresh else None)
        except LiveHalt:
            capital=dict(allocation_inr=None,available_for_new_trade_inr=None,realized_net_pnl_inr=None,committed_inr=None,broker_cash_inr=None,error='Realized costs unavailable')
        completed=[dict(decision_id=t['decision_id'],symbol=t['symbol'],closed_at=t.get('closed_at'),gross_pnl=t.get('gross_pnl'),charges=t.get('charges'),net_pnl=t.get('net_pnl')) for t in trades if t['status']=='CLOSED']
        open_trades=[dict(symbol=t['symbol'],status=t['status'],bought=t.get('entry',{}).get('filled',0),sold=sum(s.get('filled',0) for s in t['sells']),halted=t.get('halted',False),stop=t['stop'],target=t['target']) for t in trades if t['status'] not in ('CLOSED','CANCELLED','REJECTED')]
        daily=None if any(t.get('net_pnl') is None for t in completed) else sum(t['net_pnl'] for t in completed if (t.get('closed_at') or '')[:10]==self.clock().date().isoformat())
        heartbeat=self.store.metadata('runner_heartbeat') or {'status':'NOT_RUNNING'}
        try:
            if (self.clock()-datetime.fromisoformat(heartbeat['checked_at'])).total_seconds()>30:
                heartbeat['status']='NOT_RUNNING'
        except (KeyError,ValueError): heartbeat['status']='NOT_RUNNING'
        return dict(demo=False,connection=connection,capital=capital,daily_pnl=daily,paused=(self.root/'PAUSE').exists(),runner=heartbeat,
            open_trades=open_trades,completed=completed[-50:][::-1],positions=broker.get('positions',[]),orders=broker.get('orders',[]),
            login_ready=bool(self.account_id and self.api_key and self.api_secret),generated_at=self.clock().isoformat())


def serve(app, host, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self): self.dispatch()
        def do_POST(self): self.dispatch()
        def dispatch(self):
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<0 or length>4096: raise ValueError()
                status,headers,body=app.handle(self.command,self.path,self.headers,self.rfile.read(length),self.client_address[0])
            except Exception:
                status,headers,body=app._reply(400,'Request could not be processed')
            self.send_response(status)
            for key,value in headers.items(): self.send_header(key,value)
            self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass # callback query contains a credential; never log it
    server=ThreadingHTTPServer((host,port),Handler)
    server.daemon_threads=True
    server.serve_forever()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8080)
    parser.add_argument('--root',type=Path,default=LIVE_ROOT); parser.add_argument('--config',type=Path,default=Path('config/live.json'))
    parser.add_argument('--env-file',type=Path,default=Path('.env')); parser.add_argument('--demo',action='store_true')
    args=parser.parse_args(argv)
    try:
        if args.host not in ('127.0.0.1','localhost','::1'): raise ValueError('Bind to loopback behind an HTTPS reverse proxy')
        if args.demo:
            app=DashboardApp(args.root,f'http://127.0.0.1:{args.port}','preview-only-password',allow_local_http=True,demo=True)
        else:
            load_env_file(args.env_file,names=('DASHBOARD_PASSWORD','DASHBOARD_PUBLIC_URL','KITE_API_KEY','KITE_API_SECRET'))
            configuration=json.loads(args.config.read_text())
            app=DashboardApp(args.root,os.environ.get('DASHBOARD_PUBLIC_URL',''),os.environ.get('DASHBOARD_PASSWORD',''),
                account_id=configuration.get('account_id'),api_key=os.environ.get('KITE_API_KEY',''),api_secret=os.environ.get('KITE_API_SECRET',''),
                starting_capital=configuration.get('capital_limit_inr',10000),fee_reserve=configuration.get('fee_reserve_inr',200))
        print('Dashboard listening on loopback; '+('DEMO ONLY' if args.demo else 'private access requires sign-in'),flush=True)
        serve(app,args.host,args.port)
    except KeyboardInterrupt: return 130
    except Exception: print('Dashboard startup refused; check HTTPS origin, private password and config',flush=True); return 1


if __name__=='__main__': raise SystemExit(main())
