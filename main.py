
import json,time,requests,websocket,pandas as pd,io
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont

APP_ID="345wGq3sVWnzQ8oN83Qv4"
PAT="pat_82f11960db808e7effa721695a787675a869c99876d6b99492f9f95be6d584bc"
TG_TOKEN="8847130272:AAGen85LDrWJaCaf-MGlDMR97VElt4ybTTg"
TG_CHAT="-1004358584806"
BASE="https://api.derivws.com";SYMBOL="frxXAUUSD"
H1,M15,M5=3600,900,300;COUNT=120;STAKE_USD=10;MULTIPLIER=100
SWING_LOOKBACK=6;MAX_RISK_POINTS=6.;MIN_RISK_POINTS=1.5;PIP_SIZE=.01
MAX_TRADE_MINUTES=30
market_open=None;active=None;ws=None;aid=None

def log(x):print(x,flush=True)
def font(s,b=False):
try:return ImageFont.truetype("/system/fonts/Roboto-"+("Bold" if b else "Regular")+".ttf",s)
except:return ImageFont.load_default()

def make_img(k):
W,H=1200,675;im=Image.new("RGB",(W,H),(5,7,10));d=ImageDraw.Draw(im)
for y in range(H):
c=(4,18+int(y/H18),10) if k=="BUY" else (25+int(y/H25),4,5) if k=="SELL" else (8,8,11)
d.line((0,y,W,y),fill=c)
for x in range(40,W,70):d.line((x,80,x,H-55),fill=(35,35,35))
for y in range(100,H-60,65):d.line((30,y,W-30,y),fill=(35,35,35))
if k in ("BUY","SELL"):
col=(20,235,40) if k=="BUY" else (255,25,25)
d.text((65 if k=="BUY" else 650,55),"GOLDUSD",font=font(72,1),fill=(255,190,15))
d.text((65 if k=="BUY" else 650,135),k,font=font(100,1),fill=col)
pts=[(50,570),(180,500),(300,530),(420,430),(540,390),(660,300),(780,250),(900,180),(1080,75)] if k=="BUY" else [(70,100),(190,160),(310,180),(430,260),(550,300),(670,380),(790,450),(910,510),(1080,590)]
d.line(pts,fill=col,width=12)
elif k=="ONLINE":
d.text((55,45),"XAUUSD",font=font(55,1),fill=(255,190,15));d.text((55,110),"LIVE MARKET DATA",font=font(27),fill="white")
d.text((400,210),"GOLDUSD",font=font(100,1),fill=(255,190,15));d.text((475,315),"BOT",font=font(75,1),fill="white")
d.rounded_rectangle((390,420,810,510),20,outline=(20,255,60),width=6);d.text((470,442),"SYSTEM ONLINE",font=font(45,1),fill=(20,255,60))
d.text((390,550),"H1 → M15 → M5 | XAUUSD",font=font(30,1),fill=(255,190,15))
else:
d.text((55,45),"XAUUSD",font=font(55,1),fill=(255,190,15));d.text((55,110),"MARKET STATUS",font=font(27),fill="white")
d.text((370,170),"GOLDUSD",font=font(90,1),fill=(255,190,15));d.text((345,280),"MARKET CLOSED",font=font(65,1),fill=(240,30,30))
d.text((390,600),"H1 → M15 → M5 | XAUUSD",font=font(30,1),fill=(255,190,15))
b=io.BytesIO();im.save(b,"JPEG",quality=82);return b.getvalue()

IMG_ONLINE=make_img("ONLINE");IMG_CLOSED=make_img("CLOSED");IMG_BUY=make_img("BUY");IMG_SELL=make_img("SELL")

def tg(msg,retries=3):
if not TG_TOKEN or TG_TOKEN.startswith("COLLE_"):return False
for n in range(1,retries+1):
try:
r=requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",json={"chat_id":TG_CHAT,"text":msg},timeout=12)
if r.ok and r.json().get("ok"):return True
except Exception as e:log(f"⚠️ Telegram {n}/3: {e}")
time.sleep(n)
log("❌ Telegram indisponible");return False

def tg_photo(img,cap,retries=3):
if not TG_TOKEN or TG_TOKEN.startswith("COLLE_"):return False
for n in range(1,retries+1):
try:
f=io.BytesIO(img);f.name="goldusd.jpg"
r=requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",data={"chat_id":TG_CHAT,"caption":cap},files={"photo":f},timeout=15)
if r.ok and r.json().get("ok"):return True
except Exception as e:log(f"⚠️ Telegram photo {n}/3: {e}")
time.sleep(n)
return False

def headers():return {"Authorization":f"Bearer {PAT}","Deriv-App-ID":APP_ID,"Content-Type":"application/json"}

def accounts():
for n in range(3):
try:
r=requests.get(f"{BASE}/trading/v1/options/accounts",headers=headers(),timeout=15)
log(f"Deriv HTTP {r.status_code}")
if r.status_code==200:return r.json()
except Exception as e:log(f"⚠️ Deriv: {e}")
time.sleep(2)
return None

def demo_id(d):
a=d.get("data",[]);a=[a] if isinstance(a,dict) else a
for x in a:
if str(x.get("account_type","")).lower()=="demo":
log(f"✅ Démo: {x['account_id']}");return x["account_id"]

def connect(a):
for n in range(3):
try:
r=requests.post(f"{BASE}/trading/v1/options/accounts/{a}/otp",headers=headers(),timeout=15)
u=r.json().get("data",{}).get("url")
if not u:raise Exception("URL WS absente")
w=websocket.create_connection(u,timeout=20);w.settimeout(20);log("✅ WebSocket connecté");return w
except Exception as e:log(f"⚠️ WS {n+1}/3: {e}")
time.sleep(2*(n+1))
return None

def ws_alive(w):
try:return bool(w and w.connected)
except:return False

def reconnect():
global ws
try:
if ws:ws.close()
except:pass
ws=connect(aid)
if ws:log("✅ Reconnexion réussie")
return ws

def req(w,p,rid):
global ws
if not ws_alive(w):
if not reconnect():return None
w=ws
try:
p["req_id"]=rid;w.send(json.dumps(p))
while True:
x=json.loads(w.recv())
if x.get("req_id")==rid:return x
except Exception as e:
log(f"⚠️ WS: {e}")
if reconnect():
try:
p["req_id"]=rid+10000;ws.send(json.dumps(p))
while True:
x=json.loads(ws.recv())
if x.get("req_id")==rid+10000:return x
except Exception as e2:log(f"❌ WS reconnexion: {e2}")
return None

def balance(w):
x=req(w,{"balance":1},10)
if x and not x.get("error"):
b=x["balance"];log(f"💰 Solde: {b.get('balance')} {b.get('currency','')}")

def symbol_ok(w):
x=req(w,{"active_symbols":"brief"},20)
if not x or x.get("error"):return False
for s in x.get("active_symbols",[]):
if s.get("underlying_symbol")==SYMBOL:log("✅ XAUUSD trouvé");return True
return False

def market(w):
global market_open
x=req(w,{"active_symbols":"brief"},21)
if not x:return False
for s in x.get("active_symbols",[]):
if s.get("underlying_symbol")==SYMBOL:
op=bool(s.get("exchange_is_open",0)) and not bool(s.get("is_trading_suspended",0))
if market_open!=op:
market_open=op
tg_photo(IMG_ONLINE,"🤖 GOLDUSD BOT ONLINE\n🧭 H1 → M15 → M5\n💵 Mise: 10 USD | x100") if op else tg_photo(IMG_CLOSED,"⏸️ XAUUSD FERMÉ")
return op
return False

def candles(w,g,rid):
x=req(w,{"ticks_history":SYMBOL,"end":"latest","count":COUNT,"style":"candles","granularity":g},rid)
if not x or x.get("error"):return None
r=[]
for c in x.get("candles",[]):
try:r.append([int(c["epoch"]),float(c["open"]),float(c["high"]),float(c["low"]),float(c["close"])])
except:pass
return pd.DataFrame(r,columns=["time","open","high","low","close"]) if len(r)>=60 else None

def ind(d):
d=d.copy();d["e20"]=d.close.ewm(span=20,adjust=False).mean();d["e50"]=d.close.ewm(span=50,adjust=False).mean()
q=d.close.diff();g=q.clip(lower=0).rolling(14).mean();l=(-q.clip(upper=0)).rolling(14).mean()
d["rsi"]=100-100/(1+g/l.replace(0,float("nan")));return d

def h1(d):
x=ind(d).iloc[-1]
if x.close>x.e20>x.e50 and x.rsi>50:return"BUY"
if x.close<x.e20<x.e50 and x.rsi<50:return"SELL"
return"NEUTRAL"

def m15(d,s):
d=ind(d);x=d.iloc[-1];p=d.iloc[-2]
return x.close>x.e20>x.e50 and x.rsi>50 and x.close>p.close if s=="BUY" else x.close<x.e20<x.e50 and x.rsi<50 and x.close<p.close

def m5(d,s):
d=ind(d);x=d.iloc[-1];p=d.iloc[-2]
return x.close>x.open and x.close>p.close and x.close>x.e20 and 50<x.rsi<70 if s=="BUY" else x.close<x.open and x.close<p.close and x.close<x.e20 and 30<x.rsi<50

def levels(d,s,e):
z=d.tail(SWING_LOOKBACK);raw=e-float(z.low.min()) if s=="BUY" else float(z.high.max())-e;risk=max(MIN_RISK_POINTS,min(raw,MAX_RISK_POINTS))
if risk<=0:return None
return{"sl":round(e-risk,2) if s=="BUY" else round(e+risk,2),"tp1":round(e+risk,2) if s=="BUY" else round(e-risk,2),"tp2":round(e+risk2,2) if s=="BUY" else round(e-risk2,2),"tp3":round(e+risk3,2) if s=="BUY" else round(e-risk3,2),"risk":round(risk,2)}

def open_trade(w,s,e,L):
global active
ct="MULTUP" if s=="BUY" else"MULTDOWN";stake=round(STAKE_USD/3,2);legs=[]
for i,(lab,tp) in enumerate([("TP1",L["tp1"]),("TP2",L["tp2"]),("TP3",L["tp3"])]):
p=req(w,{"proposal":1,"amount":stake,"basis":"stake","contract_type":ct,"currency":"USD","multiplier":MULTIPLIER,"underlying_symbol":SYMBOL},700+i)
if not p or p.get("error"):log(f"❌ {lab}: proposition refusée");continue
pr=p.get("proposal",{});pid=pr.get("id");ask=pr.get("ask_price")
if not pid or ask is None:continue
b=req(w,{"buy":pid,"price":float(ask)},720+i)
if not b or b.get("error"):log(f"❌ {lab}: achat refusé");continue
cid=b.get("buy",{}).get("contract_id")
if cid:legs.append({"label":lab,"id":cid,"target":tp,"closed":False});log(f"✅ {lab} ouvert | ID {cid}")
if not legs:return False
active={"side":s,"entry":e,"sl":L["sl"],"legs":legs,"start":time.time(),"total_profit":0.0,"timeout_checked":False}
tg_photo(IMG_BUY if s=="BUY" else IMG_SELL,f"📌 SIGNAL {s}\n💵 Entrée: {e}\n🛑 SL: {L['sl']}\n🎯 TP1: {L['tp1']}\n🎯 TP2: {L['tp2']}\n🎯 TP3: {L['tp3']}\n💼 {len(legs)} position(s)\n⚖️ x{MULTIPLIER} | Mise {STAKE_USD} USD")
return True

def price(w):
x=req(w,{"ticks":SYMBOL},900)
try:return float(x["tick"]["quote"])
except:return None

===== SUIVI RÉEL DU CONTRAT =====

def contract_status(w,cid):
x=req(w,{"proposal_open_contract":1,"contract_id":cid},1000+int(str(cid)[-4:]))
if not x or x.get("error"):return None
c=x.get("proposal_open_contract",{})
try:profit=float(c.get("profit",0))
except:profit=0.0
return {"open":bool(c.get("is_open",not c.get("is_sold",False))),"sold":bool(c.get("is_sold",False)),"expired":bool(c.get("is_expired",False)),"profit":profit,"status":str(c.get("status","")).lower()}

def close_leg(w,leg):
for attempt in range(1,4):
try:
st=contract_status(w,leg["id"])
if st and not st["open"]:
return st["profit"],True
r=req(w,{"sell":leg["id"],"price":0},1100+attempt)
if r and not r.get("error"):
time.sleep(.5)
st=contract_status(w,leg["id"])
if st and not st["open"]:return st["profit"],True
except Exception as e:log(f"⚠️ Fermeture {attempt}/3: {e}")
time.sleep(1)
return None,False

def result_msg(label,profit,reason):
if profit>0:return f"🎯 {label} {reason}\n🟢 GAIN: +{profit:.2f} USD"
if profit<0:return f"🛑 {label} {reason}\n🔴 PERTE: {profit:.2f} USD"
return f"⚪ {label} {reason}\n💰 Résultat: 0.00 USD"

def monitor(w):
global active
if not active:return
s=active["side"];px=price(w)
if px is None:return
elapsed=(time.time()-active["start"])/60
for leg in active["legs"]:
if leg["closed"]:continue
st=contract_status(w,leg["id"])
if st and not st["open"]:
profit=st["profit"];leg["closed"]=True;active["total_profit"]+=profit
tg(result_msg(leg["label"],profit,"TERMINÉ"))
continue
hit=px>=leg["target"] if s=="BUY" else px<=leg["target"]
sl=px<=active["sl"] if s=="BUY" else px>=active["sl"]
if hit or sl:
profit,done=close_leg(w,leg)
if not done:log(f"⏳ {leg['label']}: fermeture non confirmée");continue
leg["closed"]=True;active["total_profit"]+=profit
tg(result_msg(leg["label"],profit,"TP TOUCHÉ" if hit else "SL TOUCHÉ"))
if elapsed>=MAX_TRADE_MINUTES and not active.get("timeout_checked"):
active["timeout_checked"]=True
for leg in active["legs"]:
if not leg["closed"]:
profit,done=close_leg(w,leg)
if done:
leg["closed"]=True;active["total_profit"]+=profit
tg(result_msg(leg["label"],profit,"FERMÉ APRÈS 30 MIN"))
if active and all(x["closed"] for x in active["legs"]):
total=active["total_profit"];tg(f"🏁 TRADE TERMINÉ\n💰 Résultat total: {total:+.2f} USD");log(f"🏁 TRADE TERMINÉ | {total:+.2f} USD");active=None

def analyse(w):
if active:return
log("\n==============================");log("📊 ANALYSE XAUUSD");log(datetime.now().strftime("🕐 %H:%M:%S"))
a=candles(w,H1,101)
if a is None:return
s=h1(a);log(f"🔵 H1: {s}")
if s=="NEUTRAL":return
b=candles(w,M15,102)
if b is None or not m15(b,s):log("🟡 M15: pas confirmé");return
log(f"🟡 M15: ✅ confirmé {s}")
c=candles(w,M5,103)
if c is None or not m5(c,s):log("🟢 M5: pas d'entrée");return
log(f"🟢 M5: ✅ entrée {s}");e=round(float(c.iloc[-1].close),2);L=levels(c,s,e)
if L:log(f"💵 Entrée: {e} | Risque: {L['risk']} points");open_trade(w,s,e,L)

def main():
global ws,aid
log("\n🚀 DÉMARRAGE GOLDUSD BOT");log("🧪 MODE DÉMO - MULTIPLICATEUR");log("🧭 H1 → M15 → M5");log(f"💵 MISE: {STAKE_USD} USD | x{MULTIPLIER}")
d=accounts()
if not d:return
aid=demo_id(d)
if not aid:return
ws=connect(aid)
if not ws:return
balance(ws)
if not symbol_ok(ws):return
market(ws);log("\n================================");log("🟢 ROBOT PRÊT");log("📡 XAUUSD LIVE");log("🎯 H1 → M15 → M5");log("================================")
while True:
try:
if not ws_alive(ws):
if not reconnect():time.sleep(10);continue
if not market(ws):time.sleep(30);continue
px=price(ws)
if px is not None:log(f"📡 LIVE {datetime.now().strftime('%H:%M:%S')} | XAUUSD={px}")
monitor(ws) if active else analyse(ws)
log("⏳ Prochaine vérification dans 30 secondes...");time.sleep(30)
except KeyboardInterrupt:break
except Exception as e:log(f"❌ ERREUR: {e}");time.sleep(5)

while True:
try:main()
except KeyboardInterrupt:break
except Exception as e:log(f"❌ CRASH: {e}");time.sleep(10)

Voilà
