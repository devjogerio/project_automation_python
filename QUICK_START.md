# 🚀 Guia Rápido de Execução

## Iniciar o Sistema

### Opção 1: Interface Gráfica (Recomendado)
```bash
python src/main.py
```

### Opção 2: Modo Headless (Sem GUI)
```bash
python src/main.py --headless
```

### Opção 3: Com Configuração Personalizada
```bash
python src/main.py --config config/custom_config.yaml --log-level DEBUG
```

## Comandos do Assistente Virtual

Assim que a GUI abrir, você pode usar os seguintes comandos no chat:

### 🕷️ **Web Scraping**
```
scrape https://exemplo.com
extract data from https://python.org
get content from https://github.com
```

### 🔍 **Busca RAG (Base Vetorial)**
```
search for information about machine learning
find documents about Python programming
what do you know about artificial intelligence
```

### 🤖 **Consultas LLM**
```
explain quantum computing
what is the capital of France
help me write a Python function
generate a summary of this text
```

### 📊 **Google Sheets**
```
sync scraping data to sheets
export search results to Google Sheets
backup conversation to sheets
```

### 💬 **Conversa Geral**
```
hello
how are you
thanks
bye
```

## Configuração Inicial

### 1. Configure suas chaves API
```bash
cp .env.example .env
nano .env  # ou use seu editor favorito
```

### 2. Configure Google Sheets (Opcional)
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto
3. Habilite Google Sheets API
4. Crie credenciais de Service Account
5. Baixe o JSON e configure no .env

### 3. Teste a instalação
```bash
python test_system.py
```

## Comandos Úteis

### Verificar status do sistema
```bash
python -c "from src.main import AutomationSystem; import asyncio; s = AutomationSystem(); print(s.get_system_status())"
```

### Executar scraping direto
```bash
python -c "from src.main import AutomationSystem; import asyncio; s = AutomationSystem(); result = asyncio.run(s.scraper.scrape_url('https://example.com')); print(result)"
```

### Buscar no banco vetorial
```bash
python -c "from src.main import AutomationSystem; import asyncio; s = AutomationSystem(); results = asyncio.run(s.vector_store.search_similar('Python programming')); print(results)"
```

## Solução de Problemas

### Erro: "Module not found"
```bash
pip install -r requirements.txt
```

### Erro: "Google API not available"
- Instale: `pip install google-api-python-client google-auth`
- Ou ignore: o sistema funcionará sem Google Sheets

### Erro: "Selenium not found"
- Instale: `pip install selenium webdriver-manager`
- Ou use apenas scraping estático

### Erro: "ChromaDB not found"
- Instale: `pip install chromadb sentence-transformers`
- Ou use apenas LLM sem banco vetorial

## Atalhos de Teclado (GUI)

- `Ctrl+N`: Nova conversa
- `Ctrl+S`: Salvar conversa
- `Ctrl+E`: Exportar para arquivo
- `Ctrl+Q`: Sair
- `F1`: Ajuda
- `F5`: Atualizar status

## Exemplos de Uso Avançado

### Pipeline Completo
```python
from src.main import AutomationSystem
import asyncio

async def pipeline_completo():
    system = AutomationSystem()
    
    # 1. Scraping
    scrape_result = await system.scraper.scrape_url("https://python.org")
    
    # 2. Armazenar em vetores
    if scrape_result['success']:
        docs = [{
            "content": scrape_result['content'],
            "metadata": {"url": scrape_result['url']}
        }]
        await system.vector_store.add_documents(docs)
    
    # 3. Buscar informações
    results = await system.vector_store.search_similar("Python features")
    
    # 4. Gerar resposta
    response = await system.llm_router.generate_response("Explain Python")
    
    print(response.content)

# Executar
asyncio.run(pipeline_completo())
```

## Suporte

- 📧 Email: suporte@automation-system.com
- 🐛 Issues: GitHub Issues
- 📖 Documentação: README.md completo
- 🧪 Testes: Execute `python test_system.py`

---

**Divirta-se automatizando! 🤖**