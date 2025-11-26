# Sistema de Automação Python com IA

Um sistema completo de automação em Python que integra web scraping, banco de dados vetorial, LLMs, Google Sheets, WhatsApp via WAHA e serviços AWS (Bedrock, S3, Lambda, API Gateway) com CI/CD e monitoramento.

## 🚀 Funcionalidades

### 1. **Web Scraping Inteligente**

- Scraping de conteúdo estático e dinâmico com Selenium
- Conformidade com robots.txt
- Tratamento robusto de erros e retry automático
- Suporte a múltiplos seletores CSS
- Extração de metadados e timestamps

### 2. **Banco de Dados Vetorial RAG**

- Armazenamento semântico com ChromaDB
- Indexação de documentos com embeddings
- Busca por similaridade com cosine similarity
- Integração com sentence-transformers
- Suporte a múltiplas coleções

### 3. **Integração Multi-LLM**

- Suporte a OpenAI GPT, LLaMA 3, Amazon Bedrock, Anthropic (Claude) e Google Gemini
- Roteamento inteligente entre provedores
- Cache de respostas para performance
- Fallback automático entre modelos
- Métricas de uso e tokens
- Preferência de provedor via `LLM_PREFERRED_PROVIDER`

### 4. **Sincronização com Google Sheets**

- Integração completa com Google Sheets API
- Sincronização automática de dados raspados
- Registro de interações com LLM
- Backup de resultados de busca RAG
- Operações em lote para eficiência

### 5. **Assistente Virtual com IA**

- Reconhecimento inteligente de intenções
- Conversação contextual com histórico
- Processamento de múltiplos tipos de queries
- Integração com todos os módulos do sistema
- Respostas naturais e contextualizadas

### 6. **Interface Gráfica Moderna**

- GUI com CustomTkinter
- Múltiplas abas para diferentes funcionalidades
- Interface de chat intuitiva
- Controles em tempo real
- Temas modernos e responsivos

### 7. **Sistema de Monitoramento**

- Logs detalhados com Loguru
- Métricas de performance
- Health checks de componentes
- Alertas de erro
- Dashboard de status
- Publicação de métricas no CloudWatch (opcional)

### 8. **Infraestrutura AWS e CI/CD**

- Template SAM com S3, Lambda e API Gateway
- Pipeline GitHub Actions para build, testes e deploy
- IAM com privilégios mínimos

### 9. **API REST v1**

- Endpoints: `/api/v1/health`, `/api/v1/llm/generate`, `/api/v1/data/fetch`
- WhatsApp (WAHA) exposto em API dedicada: `http://localhost:8001/whatsapp/*`
- Autenticação JWT (header `Authorization: Bearer <token>`)
- Documentação automática OpenAPI/Swagger em `/docs`
- Versionamento por prefixo (`/api/v1`)

### 10. **Fontes de Dados (Conectores)**

- RSS (feedparser), GitHub Issues (REST), Wikipedia (REST summary)
- Formato normalizado (`content` + `metadata`) para RAG
- Tratamento de erros e fallback por fonte

## 📋 Pré-requisitos

- Python 3.8+
- Chrome/Chromium (para Selenium)
- Google Cloud credentials (para Sheets API)
- OpenAI API key (opcional)
- AWS credenciais com acesso a Bedrock/S3/Lambda/API Gateway (opcional)
- Docker (opcional)

## 🔧 Instalação

### 1. Clone o repositório

# Webhook de eventos (com assinatura HMAC opcional)

# Gere assinatura: HMAC-SHA256(body) usando o `WEBHOOK_SECRET`

curl -s -X POST http://localhost:8001/whatsapp/webhook/events \
 -H "Content-Type: application/json" \
 -H "X-Signature: $(python - << 'PY'\nimport hmac, hashlib\nsec='topsecret'\nbody=b'{"event":"message","data":{"text":"hello"}}'\nprint(hmac.new(sec.encode(), body, hashlib.sha256).hexdigest())\nPY)" \
 -d '{"event":"message","data":{"text":"hello"}}'

```bash
git clone https://github.com/devjogerio/project_automation_python.git
cd project_automation_python
```

### 2. Configure o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com suas chaves e configurações
```

Principais variáveis:

- WAHA: `WAHA_HOST`, `WAHA_API_KEY`, `WAHA_WEBHOOK_URL`
- AWS: `AWS_REGION`, `AWS_S3_BUCKET`, `BEDROCK_MODEL_ID`
- LLM: `LLM_PREFERRED_PROVIDER` (`openai|llama|bedrock|anthropic|gemini`), `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `SAGEMAKER_ENDPOINT_NAME`, `LAMBDA_FUNCTION_NAME`

### 5. Configure Google Sheets (opcional)

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione um existente
3. Habilite a Google Sheets API
4. Crie credenciais de service account
5. Baixe o arquivo JSON de credenciais
6. Configure o SPREADSHEET_ID no .env

## 🚀 Uso

### Execução via linha de comando

```bash
# Executar GUI (CustomTkinter)
python -m src.gui.app

# Executar sem GUI (modo headless)
python src/main.py --headless

# Executar com nível de log específico
python src/main.py --log-level DEBUG

# Mostrar configuração atual e provedores LLM
python src/main.py --config
```

### API REST

```bash
python - << 'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
from api.server import create_app
from fastapi.testclient import TestClient
app = create_app()
client = TestClient(app)
print(client.get('/api/v1/health').json())
PY
```

#### Exemplos com curl

```bash
# Defina seu token JWT
TOKEN="seu_token_jwt_aqui"

# Health check
curl -s http://localhost:8000/api/v1/health

# Geração LLM (usar provider preferido ou explicitar)
curl -s -X POST http://localhost:8000/api/v1/llm/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "prompt": "Explique programação assíncrona em Python",
    "provider": "bedrock",
    "max_tokens": 512,
    "temperature": 0.7
  }'

# Coleta de dados de múltiplas fontes
curl -s -X POST http://localhost:8000/api/v1/data/fetch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "sources": [
      {"type": "rss", "url": "https://hnrss.org/frontpage"},
      {"type": "github_issues", "repo": "python/cpython"},
      {"type": "wikipedia", "query": "Asynchronous I/O"}
    ]
  }'

# WhatsApp WAHA (porta 8001)
curl -s -X POST http://localhost:8001/whatsapp/text \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"to":"5511999999999","message":"Olá 👋"}'

curl -s -X POST http://localhost:8001/whatsapp/image \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"to":"5511999999999","image_url":"https://example.com/img.png","caption":"Exemplo"}'

curl -s -X POST http://localhost:8001/whatsapp/ptt \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"to":"5511999999999","audio_base64":"QmFzZTY0QXVkaW8="}'

curl -s -X POST http://localhost:8001/whatsapp/thumb \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"to":"5511999999999","url":"https://example.com","title":"Exemplo","description":"Desc"}'

# Sessões WAHA
curl -s -X POST http://localhost:8001/whatsapp/session/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"sessao1"}'

curl -s -X POST http://localhost:8001/whatsapp/session/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"sessao1"}'

curl -s -X GET http://localhost:8001/whatsapp/session/sessao1/status \
  -H "Authorization: Bearer $TOKEN"

curl -s -X POST http://localhost:8001/whatsapp/session/stop \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"sessao1"}'

curl -s -X POST http://localhost:8001/whatsapp/webhook/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"url":"https://example.com/webhook"}'
```

### Execução da API (ASGI)

```bash
# Instalar servidor ASGI (desenvolvimento)
pip install uvicorn

# Executar API com recarregamento automático
uvicorn api.server:create_app --reload --port 8000

# API WhatsApp (WAHA)
uvicorn src.api.waha_api:create_app --reload --port 8001

### Interface Web (Django)

- Instalar dependências: `pip install -r requirements.txt`
- Migrar DB: `python manage.py migrate`
- Criar usuário: `python manage.py createsuperuser`
- Executar: `python manage.py runserver 127.0.0.1:8002`

Variáveis de ambiente relevantes:

```

DJANGO_SECRET_KEY=
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
SERVICE_JWT_TOKEN=
WAHA_BASE_URL=http://127.0.0.1:8001

```

A interface chama os endpoints WAHA com `Authorization: Bearer $SERVICE_JWT_TOKEN`.

# Acessar documentação OpenAPI/Swagger
# http://localhost:8000/docs
```

### Uso programático

```python
from src.main import AutomationSystem

# Inicializar sistema
system = AutomationSystem(
    config_path="config/config.yaml",
    headless=False,
    log_level="INFO"
)

# Iniciar assistente virtual
await system.assistant.start()

# Processar mensagem
result = await system.assistant.process_message("scrape https://example.com")
print(result['response'])

# Buscar no banco vetorial
results = await system.vector_store.search_similar("machine learning", k=5)

# Gerar resposta com LLM
response = await system.llm_router.generate_response("Explain Python")
print(response.content)

# Sincronizar com Google Sheets
await system.sheets_manager.sync_scraping_data({
    "url": "https://example.com",
    "title": "Example",
    "content": "Content"
})

# Encerrar sistema
system.shutdown()
```

## 📊 Arquitetura

### Estrutura de Módulos

```
src/
├── main.py                 # Ponto de entrada principal
├── utils/
│   ├── config.py          # Gerenciamento de configurações
│   └── logger.py          # Configuração de logs
├── scraping/
│   ├── scraper.py         # Motor de web scraping
│   └── robots.py          # Parser de robots.txt
├── rag/
│   ├── vector_store.py    # Banco de dados vetorial
│   └── embeddings.py      # Funções de embedding
├── llm/
│   └── router.py          # Roteamento e provedores LLM (OpenAI, LLaMA, Bedrock, SageMaker, Lambda, Anthropic, Gemini)
├── assistant/
│   ├── virtual_assistant.py # Assistente virtual principal
│   ├── intent_recognizer.py # Reconhecimento de intenções
│   ├── conversation_manager.py # Gerenciamento de conversas
│   └── intents/           # Handlers de intenções
├── sheets/
│   └── sync_manager.py    # Sincronização com Google Sheets
├── gui/
│   ├── main_gui.py        # Interface gráfica principal
│   └── components/        # Componentes da GUI
├── aws/
│   ├── bedrock_client.py  # Cliente Bedrock
│   └── lambdas/
│       └── webhook_handler.py # Armazena webhooks WAHA no S3
├── api/
│   └── server.py          # API REST v1 (JWT, endpoints)
├── data_sources/
│   └── connectors.py      # Conectores RSS/Wikipedia/GitHub Issues
└── infra/sam/             # Template AWS SAM
```

### Fluxo de Dados

1. **Web Scraping**: URLs → Conteúdo → Processamento → Armazenamento
2. **RAG Pipeline**: Consulta → Embedding → Busca → Contexto → LLM
3. **Assistant**: Mensagem → Intenção → Ação → Resposta
4. **Sync**: Dados → Formatação → Google Sheets API → Planilha

## 🔧 Configuração

### Arquivo de Configuração (config.yaml)

```yaml
scraping:
  default_timeout: 30
  max_retries: 3
  user_agent: 'AutomationBot/1.0'
  respect_robots_txt: true
  delay_between_requests: 1

llm:
  cache_size: 1000
  llama_context_length: 4096
  llama_model_path: null
  openai_api_key: null
  preferred_provider: null

rag:
  vector_store_path: 'data/vector_store'
  embedding_model: 'all-MiniLM-L6-v2'
  chunk_size: 1000
  chunk_overlap: 200
  max_results: 5

sheets:
  spreadsheet_id: '${GOOGLE_SHEETS_ID}'
  credentials_file: '${GOOGLE_CREDENTIALS_FILE}'
  sync_interval: 300

gui:
  theme: 'dark'
  window_size: '1200x800'
  font_size: 14

logging:
  level: 'INFO'
  file: 'logs/automation.log'
  rotation: '10 MB'
  retention: '30 days'
```

### Variáveis de Ambiente (.env)

```bash
# JWT
JWT_SECRET=
JWT_ALG=HS256

# Rate Limit
RATE_LIMIT_PER_MINUTE=60

# WAHA
WAHA_HOST=
WAHA_API_KEY=
WAHA_DASHBOARD_USERNAME=
WAHA_DASHBOARD_PASSWORD=
WAHA_WEBHOOK_URL=

# AWS
AWS_REGION=
AWS_S3_BUCKET=
BEDROCK_MODEL_ID=
SAGEMAKER_ENDPOINT_NAME=
LAMBDA_FUNCTION_NAME=

# LLM
LLM_PREFERRED_PROVIDER=
```

#### Tabela de variáveis (.env)

| Variável                  | Descrição                                  |
| ------------------------- | ------------------------------------------ | ----- | ------- | --------- | -------- |
| `JWT_SECRET`              | Segredo para assinar tokens JWT            |
| `JWT_ALG`                 | Algoritmo JWT (ex.: `HS256`)               |
| `RATE_LIMIT_PER_MINUTE`   | Limite de requisições por minuto           |
| `WAHA_HOST`               | URL do WAHA (ex.: `http://localhost:3000`) |
| `WAHA_API_KEY`            | Chave da API WAHA para `X-API-KEY`         |
| `WAHA_DASHBOARD_USERNAME` | Usuário do dashboard WAHA                  |
| `WAHA_DASHBOARD_PASSWORD` | Senha do dashboard WAHA                    |
| `WAHA_WEBHOOK_URL`        | Endpoint para receber webhooks WAHA        |
| `AWS_REGION`              | Região AWS (ex.: `us-east-1`)              |
| `AWS_S3_BUCKET`           | Bucket S3 para armazenamentos              |
| `BEDROCK_MODEL_ID`        | Modelo Bedrock (ex.: `amazon.titan-text`)  |
| `SAGEMAKER_ENDPOINT_NAME` | Nome do endpoint SageMaker                 |
| `LAMBDA_FUNCTION_NAME`    | Nome da função Lambda de LLM               |
| `LLM_PREFERRED_PROVIDER`  | Provedor padrão (`openai                   | llama | bedrock | anthropic | gemini`) |
| `ANTHROPIC_API_KEY`       | Chave da API Anthropic (Claude)            |
| `GEMINI_API_KEY`          | Chave da API Google Gemini                 |

````

## 🧪 Testes

### Executar testes

```bash
# Executar pelo comando integrado
python src/main.py --test

# Ou diretamente com pytest
pytest -v

# Testes dos endpoints WAHA
pytest tests/test_wpp_api.py -q
````

### Limpeza de Projeto (Novembro/2025)

- Remoção de dependências não utilizadas em `requirements.txt`: `scrapy`, `transformers`, `faiss-cpu`, `langchain-openai`, `prometheus-client`, `psutil`, `cryptography`, `hashlib-compat`, `mock`, `toml`
- Remoção de imports não usados: `numpy` em `src/rag/processor.py` e `src/rag/vector_store.py`; `pandas` em `src/sheets/sync_manager.py`
- Inclusão de `import re` em `src/rag/vector_store.py` para suportar tokenização no `SimpleVectorStore`
- Limpeza de artefatos de desenvolvimento: exclusão de `.mypy_cache` e `.coverage` com backup em `backups/cleanup_YYYYMMDD_HHMMSS/`
- Validação: suíte `tests/test_wpp_api.py` aprovada

### Tipos de Testes

- **Unit Tests**: Testam componentes individuais
- **Integration Tests**: Testam interação entre módulos
- **Performance Tests**: Benchmark de performance
- **Error Handling Tests**: Verificam tratamento de erros

## 🐳 Docker

### Construir imagem

```bash
docker build -t automation-system .
```

### Executar com Docker

```bash
# Executar container
docker run -d --name automation \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env \
  automation-system

# Executar com docker-compose
docker-compose up -d
```

### Docker Compose

```yaml
version: '3.8'
services:
  automation:
    build: .
    container_name: automation-system
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
      - ./.env:/app/.env
    environment:
      - DISPLAY=${DISPLAY}
    network_mode: host
    restart: unless-stopped

  monitoring:
    image: prom/prometheus:latest
    container_name: automation-monitoring
    ports:
      - '9090:9090'
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    depends_on:
      - automation
    restart: unless-stopped
```

## 📈 Monitoramento

### Métricas de Performance

- Tempo de resposta por módulo
- Taxa de sucesso de operações
- Uso de memória e CPU
- Número de tokens processados
- Quantidade de dados sincronizados

### CloudWatch (opcional)

- Namespace: `ProjectAutomation/LLM`
- Métricas: `Latency`, `Requests`, `Success`, `Errors`

### Logs e Alertas

```python
# Configurar alertas personalizados
from src.utils.logger import setup_logger

logger = setup_logger("custom")
logger.add("alerts.log", level="ERROR", rotation="1 day")

# Exemplo de alerta
logger.error("High error rate detected: {error_rate}%", error_rate=calculate_error_rate())
```

## 🔒 Segurança

### Práticas Implementadas

- Validação de entrada de dados
- Sanitização de URLs
- Rate limiting para APIs
- Criptografia de dados sensíveis
- Logs sem dados confidenciais
- Isolamento de execução
- Segredos só em `.env` (nunca em código)

### Configuração de Segurança

```yaml
security:
  validate_urls: true
  max_url_length: 2048
  blocked_domains: ['malicious.com', 'blocked.com']
  rate_limit:
    requests_per_minute: 60
    burst_limit: 10
  encryption:
    enabled: true
    key_file: 'security/encryption.key'
```

## 📚 Exemplos de Uso

### 1. Web Scraping com Múltiplas URLs

```python
# Configurar múltiplas URLs para scraping
urls = [
    "https://example1.com",
    "https://example2.com",
    "https://example3.com"
]

# Definir seletores específicos
selectors = {
    "title": "h1.main-title",
    "content": "div.content",
    "author": "span.author-name"
}

# Executar scraping em lote
results = await system.scraper.scrape_multiple(urls, selectors=selectors)

# Processar resultados
for result in results:
    if result.get('success'):
        print(f"Scraped: {result['title']}")
        # Armazenar em vetores
        await system.vector_store.add_documents([{
            "content": result['content'],
            "metadata": {
                "url": result['url'],
                "title": result['title'],
                "author": result.get('author', 'Unknown')
            }
        }])
```

### 2. Consulta RAG com Contexto

```python
# Buscar informações relevantes
query = "What are the latest trends in machine learning?"
search_results = await system.vector_store.search_similar(query, k=3)

# Construir contexto com resultados
context = "\n".join([result['content'] for result in search_results])

# Gerar resposta contextualizada
enhanced_prompt = f"""
Based on the following context:
{context}

Answer this question: {query}
"""

response = await system.llm_router.generate_response(enhanced_prompt)
print(response.content)
```

### 3. Automação com Assistente Virtual

```python
# Configurar comandos personalizados
commands = [
    "scrape https://news.ycombinator.com and summarize the top stories",
    "search for articles about Python async programming",
    "create a summary of all findings and sync to Google Sheets"
]

# Executar sequência de comandos
results = []
for command in commands:
    result = await system.assistant.process_message(command)
    results.append(result)
    print(f"Command: {command}")
    print(f"Response: {result['response']}")
    print("-" * 50)
```

### 4. Monitoramento e Relatórios

```python
# Gerar relatório de sistema
status = system.get_system_status()

# Análise de componentes
for component, info in status['components'].items():
    if info['status'] != 'operational':
        logger.warning(f"Component {component} is {info['status']}")

# Métricas de performance
performance = status['performance']
print(f"Total operations: {performance['total_operations']}")
print(f"Success rate: {performance['success_rate']:.2%}")
print(f"Average response time: {performance['avg_response_time']:.2f}s")
```

## 🛠️ Desenvolvimento

### Configurar ambiente de desenvolvimento

```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Configurar pre-commit hooks
pre-commit install

# Executar linting
flake8 src/
black src/
isort src/

# Executar type checking
mypy src/
```

### Estrutura de Branches

```
main         # Código estável
├── develop  # Desenvolvimento
├── feature/ # Novas funcionalidades
├── bugfix/  # Correções de bugs
└── hotfix/  # Correções críticas
```

### Contribuindo

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/amazing-feature`)
3. Commit suas mudanças (`git commit -m 'Add some amazing feature'`)
4. Push para a branch (`git push origin feature/amazing-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- [OpenAI](https://openai.com/) pela API GPT
- [ChromaDB](https://www.trychroma.com/) pelo banco de dados vetorial
- [Loguru](https://github.com/Delgan/loguru) pelo sistema de logs
- [pytest](https://pytest.org/) pelo framework de testes

## 📞 Suporte

Para suporte, envie um email para suporte@automation-system.com ou abra uma issue no GitHub.

## 📈 Roadmap

- [ ] API REST completa
- [x] Suporte a Amazon Bedrock (Anthropic, Cohere, Titan)
- [x] Provedores SageMaker e Lambda
- [x] Integração WAHA (WhatsApp HTTP API)
- [x] Monitoramento com CloudWatch
- [ ] Suporte a mais LLMs (Claude, Gemini)
- [ ] Dashboard web com React
- [ ] Integração com mais fontes de dados
- [ ] Sistema de plugins
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Multi-language support

---

**Desenvolvido com ❤️ pela equipe Automation System**

### 3.1 **Provedores AWS adicionais**

- `SageMakerProvider`: invocação de endpoints gerenciados
- `LambdaProvider`: invocação de funções que processam prompts
- Parsing específico por família de modelos (Anthropic, Cohere, Titan)
- Métricas no CloudWatch (latência, erros, requisições)

### 3.2 **WhatsApp (WAHA)**

- Cliente WAHA (WhatsApp HTTP API) com autenticação por `X-API-KEY`
- Suporte a sessões, envio/recebimento e webhooks
- Armazenamento de webhooks em S3 via Lambda

# Sistema_de_Automacao_Python_com_IA
### GUI CustomTkinter

```bash
cd project_automation_python
python -m venv .venv && . .venv/bin/activate
pip install customtkinter Pillow httpx loguru
export WAHA_HOST="http://localhost:3000"  # ou configure no .env
export WAHA_API_KEY="seu_token"
python -m src.gui.app
```

Notas:
- O `.env.example` lista `WAHA_HOST` e `WAHA_API_KEY`. Não versionar valores reais.
- A GUI usa transição suave entre temas e executor assíncrono para chamadas WAHA.
