from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx, asyncio, logging, os, json
from datetime import datetime

app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

USERS_URL    = os.getenv("USERS_URL",    "http://localhost:5001")
PRODUCTS_URL = os.getenv("PRODUCTS_URL", "http://localhost:5002")
REPLICA_URL  = os.getenv("REPLICA_URL",  "http://localhost:5012")
ORDERS_URL   = os.getenv("ORDERS_URL",   "http://localhost:5003")

SERVICES = {
    "users":    USERS_URL,
    "products": PRODUCTS_URL,
    "orders":   ORDERS_URL,
}

service_status = {name: True for name in SERVICES}
replica_status = True
read_replica_turn = 0

async def check_service(name: str, url: str):
    global service_status
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                r = await client.get(f"{url}/health")
                if r.status_code == 200:
                    if not service_status.get(name, True):
                        log.info(f"[HEARTBEAT] {name} RECUPERADO em {datetime.utcnow()}")
                    service_status[name] = True
                    return
        except Exception:
            pass
    if service_status.get(name, True):
        log.warning(f"[HEARTBEAT] {name} FALHOU em {datetime.utcnow()}")
    service_status[name] = False

async def check_replica():
    global replica_status
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                r = await client.get(f"{REPLICA_URL}/health")
                if r.status_code == 200:
                    if not replica_status:
                        log.info(f"[HEARTBEAT] products-replica RECUPERADA em {datetime.utcnow()}")
                    replica_status = True
                    return
        except Exception:
            pass
    if replica_status:
        log.warning(f"[HEARTBEAT] products-replica FALHOU em {datetime.utcnow()}")
    replica_status = False

@app.on_event("startup")
async def start_heartbeat():
    async def loop():
        while True:
            await asyncio.gather(
                *[check_service(name, url) for name, url in SERVICES.items()],
                check_replica()
            )
            await asyncio.sleep(5)
    asyncio.create_task(loop())

async def proxy(method: str, url: str, request: Request, body=None):
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length")}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.request(
                method, url,
                headers=headers,
                content=body or await request.body(),
                params=dict(request.query_params),
            )
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        raise HTTPException(502, f"Erro ao contactar serviço: {e}")

@app.api_route("/users/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def users_proxy(path: str, request: Request):
    if not service_status["users"]:
        raise HTTPException(503, "Serviço de usuários indisponível")
    return await proxy(request.method, f"{USERS_URL}/users/{path}", request)

@app.api_route("/products", methods=["GET"])
@app.api_route("/products/{path:path}", methods=["GET"])
async def products_read(request: Request, path: str = ""):
    global read_replica_turn
    if not service_status["products"] and not replica_status:
        raise HTTPException(503, "Serviço de produtos indisponível")
    targets = []
    if service_status["products"]: targets.append(PRODUCTS_URL)
    if replica_status:             targets.append(REPLICA_URL)
    url_base = targets[read_replica_turn % len(targets)]
    read_replica_turn += 1
    full_path = f"/products/{path}" if path else "/products"
    return await proxy("GET", f"{url_base}{full_path}", request)

@app.api_route("/products", methods=["POST"])
@app.api_route("/products/{path:path}", methods=["POST","PUT","DELETE"])
async def products_write(request: Request, path: str = ""):
    if not service_status["products"]:
        raise HTTPException(503, "Serviço de produtos indisponível")
    body = await request.body()
    full_path = f"/products/{path}" if path else "/products"
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length")}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            primary = await client.request(
                request.method, f"{PRODUCTS_URL}{full_path}",
                headers=headers, content=body,
                params=dict(request.query_params),
            )
        if replica_status and primary.status_code in (200, 201):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        f"{REPLICA_URL}/products/_sync",
                        json=primary.json()
                    )
            except Exception as e:
                log.warning(f"[REPLICA] Falha ao propagar: {e}")
        return JSONResponse(status_code=primary.status_code, content=primary.json())
    except Exception as e:
        raise HTTPException(502, f"Erro ao contactar serviço: {e}")

@app.api_route("/orders/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def orders_proxy(path: str, request: Request):
    if not service_status["orders"]:
        raise HTTPException(503, "Serviço de pedidos indisponível")
    return await proxy(request.method, f"{ORDERS_URL}/orders/{path}", request)

@app.api_route("/orders", methods=["GET","POST"])
async def orders_proxy_root(request: Request):
    if not service_status["orders"]:
        raise HTTPException(503, "Serviço de pedidos indisponível")
    return await proxy(request.method, f"{ORDERS_URL}/orders", request)

@app.get("/health")
def health():
    return {"gateway": "ok", "services": service_status, "replica": replica_status}