import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .database import Base, engine, get_db
from .models import CartItem, CustomerSession, DetectionEvent, Product
from .schemas import CartAdd, CartRemove, EventCreate, PaymentRequest, SessionCreate

app = FastAPI(title="OmniMart AI API", version="1.0.0", description="Demo autonomous retail checkout API. Payments are simulated.")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv("OMNIMART_CORS_ORIGINS", "*").split(",")], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
app.mount("/smart-checkout", StaticFiles(directory=PROJECT_ROOT / "smart-checkout", html=True), name="checkout-site")
SECRET = os.getenv("OMNIMART_JWT_SECRET", "local-demo-secret-change-me")
ALGORITHM = "HS256"
PRODUCTS = [
 ("p1","Bananas","Fresh produce",49, ["banana"],"🍌"),("p2","Red Apple","Fresh produce",35,["apple"],"🍎"),("p3","Orange Juice","Drinks",120,["bottle"],"🧃"),("p4","Milk 1L","Dairy",68,["bottle"],"🥛"),("p5","Bread Loaf","Bakery",45,["bread"],"🍞"),("p6","Potato Chips","Snacks",30,["chips"],"🥔"),("p7","Water Bottle","Drinks",20,["bottle"],"💧"),("p8","Cereal Box","Pantry",185,["book"],"🥣"),("p9","Chocolate Bar","Snacks",40,["chocolate"],"🍫"),("p10","Coffee","Pantry",220,["cup"],"☕"),("p11","Yogurt Cup","Dairy",55,["cup"],"🥛"),("p12","Eggs (6 pack)","Dairy",72,["eggs"],"🥚"),("p13","Tomatoes","Fresh produce",42,["tomato"],"🍅"),("p14","Soap Bar","Household",38,["soap"],"🧼")]

@app.get("/", include_in_schema=False)
async def home():
    return RedirectResponse(url="/smart-checkout/")

@app.get("/cctv_analyser.html", include_in_schema=False)
async def cctv_page():
    return FileResponse(PROJECT_ROOT / "cctv_analyser.html")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        from sqlalchemy import insert
        for pid,name,category,price,labels,emoji in PRODUCTS:
            await conn.execute(insert(Product).prefix_with("OR IGNORE").values(id=pid,name=name,category=category,price=price,stock=100,labels=labels,emoji=emoji,active=True))

@app.get("/api/health")
async def health(): return {"status":"ok","service":"OmniMart AI","payment_mode":"simulated"}

@app.get("/api/products")
async def products(db: AsyncSession = Depends(get_db)):
    rows=(await db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.name))).all()
    return [{"id":p.id,"name":p.name,"category":p.category,"price":p.price,"stock":p.stock,"labels":p.labels,"emoji":p.emoji} for p in rows]

@app.post("/api/sessions",status_code=201)
async def create_session(body:SessionCreate,db:AsyncSession=Depends(get_db)):
    s=CustomerSession(id=str(uuid4()),source=body.source);db.add(s);await db.commit()
    return {"id":s.id,"status":s.status,"created_at":s.created_at}

@app.get("/api/sessions")
async def list_sessions(limit:int=100,db:AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(CustomerSession).options(selectinload(CustomerSession.items)).order_by(CustomerSession.created_at.desc()).limit(min(limit,500)))).unique().all()
    return [{"id":s.id,"status":s.status,"source":s.source,"total":s.total,"created_at":s.created_at,"item_count":sum(i.quantity for i in s.items)} for s in rows]

@app.post("/api/sessions/{session_id}/cart")
async def add_cart(session_id:str,body:CartAdd,db:AsyncSession=Depends(get_db)):
    s=await _session(db,session_id)
    if s.status!="active": raise HTTPException(409,"Session is not active")
    p=await db.get(Product,body.product_id)
    if not p or not p.active: raise HTTPException(404,"Product not found")
    item=await db.scalar(select(CartItem).where(CartItem.session_id==session_id,CartItem.product_id==p.id))
    if item: item.quantity+=body.quantity;item.source=body.source
    else: db.add(CartItem(session_id=session_id,product_id=p.id,quantity=body.quantity,unit_price=p.price,source=body.source))
    db.add(DetectionEvent(session_id=session_id,event_type="cart_add",payload={"product_id":p.id,"quantity":body.quantity,"source":body.source}))
    await db.commit();return await _cart_response(db,session_id)

@app.delete("/api/sessions/{session_id}/cart/{product_id}")
async def remove_cart(session_id:str,product_id:str,body:CartRemove|None=None,db:AsyncSession=Depends(get_db)):
    await _session(db,session_id);item=await db.scalar(select(CartItem).where(CartItem.session_id==session_id,CartItem.product_id==product_id))
    if not item: raise HTTPException(404,"Cart item not found")
    if body and body.quantity and body.quantity<item.quantity:item.quantity-=body.quantity
    else:await db.delete(item)
    await db.commit();return await _cart_response(db,session_id)

@app.post("/api/sessions/{session_id}/events",status_code=201)
async def event(session_id:str,body:EventCreate,db:AsyncSession=Depends(get_db)):
    await _session(db,session_id);e=DetectionEvent(session_id=session_id,event_type=body.event_type,payload=body.payload);db.add(e);await db.commit()
    return {"id":e.id,"event_type":e.event_type,"created_at":e.created_at}

@app.post("/api/sessions/{session_id}/checkout")
async def checkout(session_id:str,body:PaymentRequest,db:AsyncSession=Depends(get_db)):
    if body.payment_method not in {"upi","card","cash","wallet"}:raise HTTPException(422,"Payment method must be upi, card, cash or wallet")
    s=await _session(db,session_id,with_items=True)
    if s.status!="active":raise HTTPException(409,"Session is not active")
    if not s.items:raise HTTPException(400,"Cart is empty")
    total=round(sum(i.quantity*i.unit_price for i in s.items),2)
    if not body.simulate_success:return {"status":"pending","total":total,"session_id":s.id}
    s.total=total;s.payment_method=body.payment_method;s.status="paid";s.completed_at=datetime.now(timezone.utc)
    payload={"sub":s.id,"total":total,"payment_method":body.payment_method,"iat":datetime.now(timezone.utc),"exp":datetime.now(timezone.utc)+timedelta(minutes=20)}
    s.exit_token=jwt.encode(payload,SECRET,algorithm=ALGORITHM)
    db.add(DetectionEvent(session_id=s.id,event_type="payment_approved",payload={"method":body.payment_method,"total":total}));await db.commit()
    return {"status":"paid","session_id":s.id,"total":total,"payment_method":s.payment_method,"exit_token":s.exit_token}

@app.post("/api/exit/verify")
async def verify_exit(token:str,db:AsyncSession=Depends(get_db)):
    try:claims=jwt.decode(token,SECRET,algorithms=[ALGORITHM]);sid=claims["sub"]
    except Exception:raise HTTPException(401,"Invalid or expired exit pass")
    s=await db.get(CustomerSession,sid)
    if not s or s.status!="paid" or s.exit_token!=token:raise HTTPException(401,"Exit pass is not valid for an active paid session")
    return {"valid":True,"session_id":sid,"total":s.total,"payment_method":s.payment_method}

async def _session(db,sid,with_items=False):
    q=select(CustomerSession).where(CustomerSession.id==sid)
    if with_items:q=q.options(selectinload(CustomerSession.items).selectinload(CartItem.product))
    s=await db.scalar(q)
    if not s:raise HTTPException(404,"Session not found")
    return s
async def _cart_response(db,sid):
    s=await _session(db,sid,True);return _serialize_session(s)
def _serialize_session(s):
    items=[{"product_id":i.product_id,"name":i.product.name,"price":i.unit_price,"quantity":i.quantity,"source":i.source} for i in s.items]
    return {"id":s.id,"status":s.status,"source":s.source,"total":round(sum(x["price"]*x["quantity"] for x in items),2),"items":items,"created_at":s.created_at}
