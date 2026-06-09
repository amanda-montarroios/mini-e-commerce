from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import json, os, uuid, jwt
from datetime import datetime

app = FastAPI()
bearer = HTTPBearer()

SECRET = os.getenv("JWT_SECRET", "supersecret")
DB_PATH = "data/orders.json"

os.makedirs("data", exist_ok=True)

def load_db():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH) as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")

class OrderRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/orders", status_code=201)
def create_order(req: OrderRequest, payload=Depends(verify_token)):
    orders = load_db()
    order = {
        "id": str(uuid.uuid4()),
        "user_id": req.user_id,
        "product_id": req.product_id,
        "quantity": req.quantity,
        "created_at": datetime.utcnow().isoformat()
    }
    orders.append(order)
    save_db(orders)
    return order

@app.get("/orders/{user_id}")
def get_orders(user_id: str, payload=Depends(verify_token)):
    orders = load_db()
    return [o for o in orders if o["user_id"] == user_id]