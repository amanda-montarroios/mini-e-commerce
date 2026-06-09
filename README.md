# Mini E-commerce Distribuído — Instruções de Execução

## Opção 1: Docker Compose (recomendado)

```bash
docker-compose up --build
```

Todos os serviços sobem automaticamente.

## Opção 2: Manual (sem Docker)

Instale as dependências em cada serviço:
```bash
cd users && pip install -r requirements.txt
cd ../products && pip install -r requirements.txt
cd ../orders && pip install -r requirements.txt
cd ../gateway && pip install -r requirements.txt
```

Suba cada serviço em um terminal separado:
```bash
# Terminal 1
JWT_SECRET=segredo uvicorn users.main:app --port 5001

# Terminal 2
JWT_SECRET=segredo REPLICA_ID=primary uvicorn products.main:app --port 5002

# Terminal 3
JWT_SECRET=segredo REPLICA_ID=replica uvicorn products.main:app --port 5012

# Terminal 4
JWT_SECRET=segredo uvicorn orders.main:app --port 5003

# Terminal 5
JWT_SECRET=segredo uvicorn gateway.main:app --port 5000
```

## Testando

```bash
# 1. Registrar usuário admin
curl -X POST http://localhost:5000/users/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Admin","email":"admin@test.com","password":"123","role":"admin"}'

# 2. Login
curl -X POST http://localhost:5000/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"123"}'
# Copie o token retornado

# 3. Criar produto (requer token admin)
curl -X POST http://localhost:5000/products \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Teclado","price":199.90,"stock":50}'

# 4. Listar produtos
curl http://localhost:5000/products

# 5. Criar pedido
curl -X POST http://localhost:5000/orders \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"ID_DO_USUARIO","product_id":"ID_DO_PRODUTO","quantity":1}'
```

## Simular falha no heartbeat

Derrube um serviço e observe os logs do gateway:
```bash
docker-compose stop orders
# Aguarde 10s e tente acessar /orders — retornará 503
docker-compose start orders
# O gateway registra a recuperação
```
