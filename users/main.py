from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import json, os, uuid, bcrypt, jwt
from datetime import datetime, timedelta

app = FastAPI()
bearer = HTTPBearer()

SECRET = os.getenv("JWT_SECRET", "supersecret")
DB_PATH = "data/users.json"

os.makedirs("data", exist_ok=True)

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH) as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/users/register", status_code=201)
def register(req: RegisterRequest):
    db = load_db()
    if any(u["email"] == req.email for u in db.values()):
        raise HTTPException(400, "Email já cadastrado")
    uid = str(uuid.uuid4())
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    db[uid] = {"id": uid, "name": req.name, "email": req.email,
               "password": hashed, "role": req.role}
    save_db(db)
    return {"id": uid, "name": req.name, "email": req.email}

@app.post("/users/login")
def login(req: LoginRequest):
    db = load_db()
    user = next((u for u in db.values() if u["email"] == req.email), None)
    if not user or not bcrypt.checkpw(req.password.encode(), user["password"].encode()):
        raise HTTPException(401, "Credenciais inválidas")
    token = jwt.encode({
        "userId": user["id"],
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=8)
    }, SECRET, algorithm="HS256")
    return {"token": token}

@app.get("/users/{user_id}")
def get_user(user_id: str, payload=Depends(verify_token)):
    db = load_db()
    user = db.get(user_id)
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}