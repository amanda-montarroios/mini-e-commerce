from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import json, os, uuid, jwt

app = FastAPI()
bearer = HTTPBearer()

SECRET = os.getenv("JWT_SECRET", "supersecret")
REPLICA_ID = os.getenv("REPLICA_ID", "primary")
DB_PATH = f"products/data/products_{REPLICA_ID}.json"

os.makedirs("products/data", exist_ok=True)

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH) as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

def verify_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(403, "Acesso negado: somente admins")
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")

class ProductRequest(BaseModel):
    name: str
    price: float
    stock: int

@app.get("/health")
def health():
    return {"status": "ok", "replica": REPLICA_ID}

@app.get("/products")
def list_products():
    db = load_db()
    return list(db.values())

@app.get("/products/{product_id}")
def get_product(product_id: str):
    db = load_db()
    p = db.get(product_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    return p

@app.post("/products", status_code=201)
def create_product(req: ProductRequest, _=Depends(verify_admin)):
    db = load_db()
    pid = str(uuid.uuid4())
    db[pid] = {"id": pid, "name": req.name, "price": req.price, "stock": req.stock}
    save_db(db)
    return db[pid]

@app.post("/products/_sync")
def sync_product(product: dict):
    db = load_db()
    db[product["id"]] = product
    save_db(db)
    return {"synced": True}