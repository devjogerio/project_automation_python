"""
Sistema de Automação com Web Scraping, RAG e LLMs

Script principal para inicialização e execução do sistema.
"""

import sys
import argparse
import signal
from pathlib import Path
from loguru import logger

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent))

def signal_handler(sig, frame):
    """Handler para sinais de interrupção."""
    logger.info("Sistema encerrado pelo usuário")
    sys.exit(0)

def main():
    """Função principal do sistema."""
    # Configura handler de sinais
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description="Sistema de Automação com Web Scraping, RAG e LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --gui                 # Inicia interface gráfica
  python main.py --scraping             # Executa scraping imediatamente
  python main.py --assistant            # Inicia assistente em modo texto
  python main.py --test                 # Executa testes
  python main.py --config               # Mostra configurações atuais
        """
    )
    
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Inicia interface gráfica (padrão)'
    )
    
    parser.add_argument(
        '--scraping',
        action='store_true',
        help='Executa scraping imediatamente'
    )
    
    parser.add_argument(
        '--assistant',
        action='store_true',
        help='Inicia assistente em modo texto'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Executa testes do sistema'
    )
    
    parser.add_argument(
        '--config',
        action='store_true',
        help='Mostra configurações atuais'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Executa configuração inicial'
    )
    
    args = parser.parse_args()
    
    # Se nenhum argumento, usa GUI por padrão
    if not any(vars(args).values()):
        args.gui = True
    
    try:
        # Importa módulos necessários
        from utils.config import config
        
        logger.info("🚀 Iniciando Sistema de Automação")
        logger.info(f"Versão: 1.0.0")
        logger.info(f"Diretório de trabalho: {Path.cwd()}")
        
        # Executa ação solicitada
        if args.setup:
            return run_setup()
        elif args.config:
            return show_config()
        elif args.test:
            return run_tests()
        elif args.scraping:
            return run_scraping()
        elif args.assistant:
            return run_assistant()
        elif args.gui:
            return run_gui()
        else:
            parser.print_help()
            return 0
            
    except KeyboardInterrupt:
        logger.info("Execução interrompida pelo usuário")
        return 0
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        return 1

def run_setup():
    """Executa configuração inicial do sistema."""
    logger.info("🔧 Executando configuração inicial...")
    
    try:
        from utils.config import config
        from scraping.site_manager import site_manager
        from rag.vector_store import vector_store
        
        # Cria diretórios necessários
        directories = [
            config.base_dir / "data",
            config.base_dir / "logs",
            config.base_dir / "config",
            config.base_dir / "models"
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True)
            logger.info(f"📁 Diretório criado/verificado: {directory}")
        
        # Inicializa banco vetorial
        logger.info("📊 Inicializando banco vetorial...")
        stats = vector_store.get_collection_stats()
        logger.info(f"✅ Banco vetorial pronto: {stats.get('total_documents', 0)} documentos")
        
        # Carrega sites padrão
        logger.info("🌐 Verificando sites configurados...")
        sites = site_manager.list_sites()
        logger.info(f"✅ {len(sites)} sites configurados")
        
        logger.info("✅ Configuração inicial concluída!")
        logger.info("💡 Próximos passos:")
        logger.info("   1. Configure suas chaves de API em .env")
        logger.info("   2. Ajuste configurações de sites em config/sites.json")
        logger.info("   3. Execute 'python main.py --gui' para iniciar a interface")
        
        return 0
        
    except Exception as e:
        logger.error(f"Erro na configuração inicial: {e}")
        return 1

def show_config():
    """Mostra configurações atuais do sistema."""
    logger.info("⚙️ Configurações do Sistema:")
    
    try:
        from utils.config import config
        from llm.router import llm_router
        from rag.vector_store import vector_store
        from scraping.orchestrator import scraping_orchestrator
        from sheets.sync_manager import sheets_sync
        
        # Configurações gerais
        logger.info("\n📋 Configurações Gerais:")
        logger.info(f"   Diretório base: {config.base_dir}")
        logger.info(f"   Nível de log: {config.get('LOG_LEVEL', 'INFO')}")
        logger.info(f"   Workers máximos: {config.get('performance.max_workers', 4)}")
        
        # LLMs
        logger.info("\n🤖 Provedores LLM:")
        providers = llm_router.get_available_providers()
        for provider in providers:
            stats = llm_router.get_provider_stats()[provider]
            logger.info(f"   ✅ {provider}:")
            logger.info(f"      Disponível: {stats['is_available']}")
            logger.info(f"      Requisições: {stats['request_count']}")
            logger.info(f"      Taxa de sucesso: {stats['success_rate']:.1%}")
        
        if not providers:
            logger.info("   ❌ Nenhum provedor LLM disponível")
        
        # Banco vetorial
        logger.info("\n📚 Banco Vetorial:")
        try:
            stats = vector_store.get_collection_stats()
            logger.info(f"   ✅ Documentos: {stats.get('total_documents', 0)}")
            logger.info(f"   Coleção: {stats.get('collection_name', 'N/A')}")
            logger.info(f"   Modelo de embedding: {stats.get('embedding_model', 'N/A')}")
        except Exception as e:
            logger.info(f"   ❌ Erro: {e}")
        
        # Scraping
        logger.info("\n🕷️ Sistema de Scraping:")
        status = scraping_orchestrator.get_scheduler_status()
        logger.info(f"   Agendador: {'Ativo' if status['is_running'] else 'Parado'}")
        logger.info(f"   Jobs ativos: {status['active_jobs']}")
        
        # Google Sheets
        logger.info("\n📊 Google Sheets:")
        if sheets_sync.is_configured():
            logger.info("   ✅ Configurado e disponível")
        else:
            logger.info("   ❌ Não configurado")
        
        return 0
        
    except Exception as e:
        logger.error(f"Erro ao mostrar configurações: {e}")
        return 1

def run_tests():
    """Executa testes do sistema."""
    logger.info("🧪 Executando testes...")
    
    try:
        import pytest
        import os
        
        # Define diretório de testes
        test_dir = Path(__file__).parent / "tests"
        
        if not test_dir.exists():
            logger.warning(f"Diretório de testes não encontrado: {test_dir}")
            logger.info("Criando testes básicos...")
            create_basic_tests()
        
        # Executa testes
        logger.info(f"Executando testes em: {test_dir}")
        exit_code = pytest.main([str(test_dir), "-v"])
        
        if exit_code == 0:
            logger.info("✅ Todos os testes passaram!")
        else:
            logger.warning(f"⚠️  Alguns testes falharam (código: {exit_code})")
        
        return exit_code
        
    except ImportError:
        logger.error("pytest não está instalado. Instale com: pip install pytest")
        return 1
    except Exception as e:
        logger.error(f"Erro ao executar testes: {e}")
        return 1

def run_scraping():
    """Executa scraping imediatamente."""
    logger.info("🕷️ Iniciando scraping...")
    
    try:
        from scraping.orchestrator import scraping_orchestrator
        
        # Executa scraping
        result = scraping_orchestrator.scrape_all_enabled_sites()
        
        # Analisa resultados
        success_count = sum(1 for r in result.values() if 'error' not in r)
        total_count = len(result)
        
        logger.info(f"✅ Scraping concluído: {success_count}/{total_count} sucessos")
        
        # Mostra detalhes
        for site_name, site_result in result.items():
            if 'error' in site_result:
                logger.error(f"   ❌ {site_name}: {site_result['error']}")
            else:
                logger.success(f"   ✅ {site_name}: Sucesso")
        
        return 0 if success_count > 0 else 1
        
    except Exception as e:
        logger.error(f"Erro ao executar scraping: {e}")
        return 1

def run_assistant():
    """Executa assistente em modo texto."""
    logger.info("🤖 Iniciando Assistente Virtual (modo texto)")
    
    try:
        from assistant.virtual_assistant import virtual_assistant
        
        print("\n" + "="*50)
        print("🤖 Assistente Virtual - Modo Texto")
        print("Digite 'sair' para encerrar ou 'ajuda' para comandos")
        print("="*50 + "\n")
        
        while True:
            try:
                user_input = input("Você: ").strip()
                
                if user_input.lower() in ['sair', 'exit', 'quit']:
                    print("Assistente: Até logo! 👋")
                    break
                
                if not user_input:
                    continue
                
                # Processa mensagem
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                response = loop.run_until_complete(
                    virtual_assistant.process_message(user_input)
                )
                
                loop.close()
                
                print(f"Assistente: {response['text']}")
                
                # Mostra dados adicionais se houver
                if 'data' in response and response['type'] in ['system_info', 'scraping_status']:
                    print(f"📊 Dados adicionais: {json.dumps(response['data'], indent=2)}")
                
            except KeyboardInterrupt:
                print("\nAssistente: Até logo! 👋")
                break
            except Exception as e:
                print(f"❌ Erro: {e}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Erro ao executar assistente: {e}")
        return 1

def run_gui():
    """Executa interface gráfica."""
    logger.info("🎨 Iniciando Interface Gráfica")
    
    try:
        from gui.main_gui import main as gui_main
        
        gui_main()
        return 0
        
    except Exception as e:
        logger.error(f"Erro ao executar interface gráfica: {e}")
        return 1

def create_basic_tests():
    """Cria testes básicos se não existirem."""
    test_dir = Path(__file__).parent / "tests"
    test_dir.mkdir(exist_ok=True)
    
    # Cria arquivo de teste básico
    test_file = test_dir / "test_basic.py"
    
    test_content = '''"""
Testes básicos do sistema de automação.
"""

import pytest
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_config_loading():
    """Testa carregamento de configurações."""
    from utils.config import config
    
    assert config is not None
    assert hasattr(config, 'base_dir')
    assert hasattr(config, 'settings')

def test_vector_store_initialization():
    """Testa inicialização do banco vetorial."""
    from rag.vector_store import vector_store
    
    assert vector_store is not None
    assert hasattr(vector_store, 'collection')

def test_site_manager():
    """Testa gerenciador de sites."""
    from scraping.site_manager import site_manager
    
    assert site_manager is not None
    sites = site_manager.list_sites()
    assert isinstance(sites, list)

def test_llm_router():
    """Testa roteador LLM."""
    from llm.router import llm_router
    
    assert llm_router is not None
    providers = llm_router.get_available_providers()
    assert isinstance(providers, list)

def test_virtual_assistant():
    """Testa assistente virtual."""
    from assistant.virtual_assistant import virtual_assistant
    
    assert virtual_assistant is not None
    stats = virtual_assistant.get_stats()
    assert isinstance(stats, dict)
'''
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    logger.info(f"Testes básicos criados em: {test_file}")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)