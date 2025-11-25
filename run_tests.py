#!/usr/bin/env python3
"""
Script de execução de testes para o Sistema de Automação
Executa todos os testes com diferentes configurações e gera relatórios
"""

import subprocess
import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime


def run_command(command, description):
    """Executa um comando e retorna resultado"""
    print(f"\n{'='*60}")
    print(f"Executando: {description}")
    print(f"Comando: {command}")
    print('='*60)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCESSO")
            return True, result.stdout
        else:
            print(f"❌ {description} - FALHOU")
            print(f"Erro: {result.stderr}")
            return False, result.stderr
            
    except Exception as e:
        print(f"❌ {description} - ERRO: {e}")
        return False, str(e)


def generate_test_report(results):
    """Gera relatório de testes"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results.values() if r["success"]),
            "failed": sum(1 for r in results.values() if not r["success"])
        },
        "results": results
    }
    
    # Salvar relatório JSON
    report_file = Path("test_reports") / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Gerar relatório HTML simples
    html_report = generate_html_report(report)
    html_file = report_file.with_suffix('.html')
    
    with open(html_file, 'w') as f:
        f.write(html_report)
    
    return report_file, html_file


def generate_html_report(report):
    """Gera relatório HTML"""
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Testes - Sistema de Automação</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ccc; }}
        .test-result.passed {{ border-left-color: green; background: #f0fff0; }}
        .test-result.failed {{ border-left-color: red; background: #fff0f0; }}
        .details {{ margin-top: 10px; font-family: monospace; font-size: 12px; }}
        pre {{ background: #f8f8f8; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Relatório de Testes - Sistema de Automação</h1>
        <p>Data: {report['timestamp']}</p>
    </div>
    
    <div class="summary">
        <h2>Resumo</h2>
        <p>Total de testes: {report['summary']['total']}</p>
        <p class="passed">Passou: {report['summary']['passed']}</p>
        <p class="failed">Falhou: {report['summary']['failed']}</p>
        <p>Taxa de sucesso: {(report['summary']['passed'] / report['summary']['total'] * 100):.1f}%</p>
    </div>
    
    <div class="results">
        <h2>Resultados Detalhados</h2>
        {''.join(generate_test_result_html(name, result) for name, result in report['results'].items())}
    </div>
</body>
</html>
"""
    return html


def generate_test_result_html(name, result):
    """Gera HTML para resultado individual de teste"""
    status_class = "passed" if result["success"] else "failed"
    status_text = "✅ Passou" if result["success"] else "❌ Falhou"
    
    details = f"<pre>{result['output'][:1000]}</pre>" if result["output"] else ""
    
    return f"""
    <div class="test-result {status_class}">
        <h3>{name} - {status_text}</h3>
        <div class="details">
            {details}
        </div>
    </div>
    """


def main():
    """Função principal de execução de testes"""
    print("🧪 Iniciando execução de testes do Sistema de Automação")
    print(f"Python: {sys.version}")
    print(f"Diretório atual: {Path.cwd()}")
    
    # Verificar se estamos no diretório correto
    if not (Path.cwd() / "src").exists():
        print("❌ Erro: Este script deve ser executado do diretório raiz do projeto")
        sys.exit(1)
    
    # Criar diretório de relatórios
    Path("test_reports").mkdir(exist_ok=True)
    
    results = {}
    
    # 1. Testes unitários básicos
    results["unit_tests"] = {
        "success": False,
        "output": "",
        "command": "pytest tests/test_config.py tests/test_scraping.py tests/test_rag.py tests/test_llm.py -v"
    }
    
    # 2. Testes de componentes individuais
    test_modules = [
        ("config_tests", "tests/test_config.py"),
        ("scraping_tests", "tests/test_scraping.py"),
        ("rag_tests", "tests/test_rag.py"),
        ("llm_tests", "tests/test_llm.py"),
        ("sheets_tests", "tests/test_sheets.py"),
        ("assistant_tests", "tests/test_assistant.py"),
    ]
    
    for name, test_file in test_modules:
        if Path(test_file).exists():
            command = f"pytest {test_file} -v --tb=short"
            success, output = run_command(command, f"Testes de {name}")
            results[name] = {
                "success": success,
                "output": output,
                "command": command
            }
    
    # 3. Testes de integração
    if Path("tests/test_integration.py").exists():
        command = "pytest tests/test_integration.py -v -m 'not performance'"
        success, output = run_command(command, "Testes de Integração")
        results["integration_tests"] = {
            "success": success,
            "output": output,
            "command": command
        }
    
    # 4. Testes de performance (opcional)
    if Path("tests/test_integration.py").exists():
        command = "pytest tests/test_integration.py -v -m performance"
        success, output = run_command(command, "Testes de Performance")
        results["performance_tests"] = {
            "success": success,
            "output": output,
            "command": command
        }
    
    # 5. Verificação de cobertura
    command = "pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=70"
    success, output = run_command(command, "Verificação de Cobertura")
    results["coverage_check"] = {
        "success": success,
        "output": output,
        "command": command
    }
    
    # 6. Testes de linting e qualidade
    quality_checks = [
        ("flake8", "flake8 src/ --max-line-length=100 --ignore=E203,W503"),
        ("black", "black --check src/"),
        ("isort", "isort --check-only src/"),
    ]
    
    for name, command in quality_checks:
        success, output = run_command(command, f"Check {name}")
        results[f"quality_{name}"] = {
            "success": success,
            "output": output,
            "command": command
        }
    
    # Gerar relatório final
    print("\n📊 Gerando relatório de testes...")
    json_file, html_file = generate_test_report(results)
    
    # Estatísticas finais
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r["success"])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n📈 Estatísticas Finais:")
    print(f"Total de testes executados: {total_tests}")
    print(f"Testes passados: {passed_tests}")
    print(f"Testes falhados: {failed_tests}")
    print(f"Taxa de sucesso: {success_rate:.1f}%")
    print(f"\n📁 Relatórios gerados:")
    print(f"JSON: {json_file}")
    print(f"HTML: {html_file}")
    
    # Abrir relatório HTML no navegador (opcional)
    if success_rate < 100:
        print(f"\n⚠️  Alguns testes falharam. Verifique o relatório HTML para detalhes.")
        print(f"Abra: {html_file}")
    else:
        print(f"\n✅ Todos os testes passaram com sucesso!")
    
    # Retornar código de saída apropriado
    sys.exit(0 if success_rate >= 80 else 1)  # Sucesso se 80%+ passou


if __name__ == "__main__":
    main()