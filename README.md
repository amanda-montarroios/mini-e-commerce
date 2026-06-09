# Mini E-commerce Distribuído — Instruções de Execução

## Pré-requisitos

- Python 3.11+
- Docker e Docker Compose (para a Opção 1)
- OpenSSL (já incluso no Git for Windows)

## Gerar certificados TLS (obrigatório antes de subir)

```bash
cd certs
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
cd ..
```

No Windows (PowerShell):
```powershell
cd certs
& "C:\Program Files\Git\usr\bin\openssl.exe" req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
cd ..
```

---

## Opção 1: Docker Compose (recomendado)

```bash
docker-compose up --build
```

Todos os serviços sobem automaticamente com TLS habilitado.

---

## Opção 2: Manual (sem Docker)

Instale as dependências em cada serviço:

```powershell
cd users; pip install -r requirements.txt; cd ..
cd products; pip install -r requirements.txt; cd ..
cd orders; pip install -r requirements.txt; cd ..
cd gateway; pip install -r requirements.txt; cd ..
```

Suba cada serviço em um terminal separado:

```powershell
# Terminal 1 — Usuários
$env:JWT_SECRET="segredo"; uvicorn main:app --port 5001 --ssl-keyfile ../certs/key.pem --ssl-certfile ../certs/cert.pem

# Terminal 2 — Produtos (primária)
$env:JWT_SECRET="segredo"; $env:REPLICA_ID="primary"; uvicorn main:app --port 5002 --ssl-keyfile ../certs/key.pem --ssl-certfile ../certs/cert.pem

# Terminal 3 — Produtos (réplica)
$env:JWT_SECRET="segredo"; $env:REPLICA_ID="replica"; uvicorn main:app --port 5012 --ssl-keyfile ../certs/key.pem --ssl-certfile ../certs/cert.pem

# Terminal 4 — Pedidos
$env:JWT_SECRET="segredo"; uvicorn main:app --port 5003 --ssl-keyfile ../certs/key.pem --ssl-certfile ../certs/cert.pem

# Terminal 5 — Gateway
$env:JWT_SECRET="segredo"; uvicorn main:app --port 5000
```

---

## Acessando o sistema

| Recurso | URL |
|---|---|
| Dashboard de monitoramento | http://localhost:5000/dashboard |
| Health do gateway | http://localhost:5000/health |
| API de usuários | http://localhost:5000/users/... |
| API de produtos | http://localhost:5000/products |
| API de pedidos | http://localhost:5000/orders |

---

## Testando via PowerShell

```powershell
# 1. Registrar usuário admin
Invoke-RestMethod -Uri http://localhost:5000/users/register `
  -Method POST -ContentType "application/json" `
  -Body '{"name":"Admin","email":"admin@test.com","password":"123","role":"admin"}'

# 2. Login e guardar token
$token = (Invoke-RestMethod -Uri http://localhost:5000/users/login `
  -Method POST -ContentType "application/json" `
  -Body '{"email":"admin@test.com","password":"123"}').token

# 3. Criar produto (requer token admin)
$produto = Invoke-RestMethod -Uri http://localhost:5000/products `
  -Method POST -ContentType "application/json" `
  -Headers @{Authorization="Bearer $token"} `
  -Body '{"name":"Teclado","price":199.90,"stock":50}'

# 4. Listar produtos
Invoke-RestMethod http://localhost:5000/products

# 5. Criar pedido
Invoke-RestMethod -Uri http://localhost:5000/orders `
  -Method POST -ContentType "application/json" `
  -Headers @{Authorization="Bearer $token"} `
  -Body "{`"user_id`":`"ID_DO_USUARIO`",`"product_id`":`"$($produto.id)`",`"quantity`":1}"
```

---

## Simular falha no heartbeat

```bash
# Derruba o serviço de pedidos
docker-compose stop orders

# Aguarde 10s — o gateway registra a falha no log
# Acesse http://localhost:5000/dashboard para ver o status offline
# Tente acessar /orders — retornará 503

# Sobe novamente
docker-compose start orders
# Após 10s o gateway registra a recuperação e o dashboard volta a verde
```

---
