# Guia de Versionamento por Nível (Júnior, Pleno, Sênior)

Documento didático com exemplos práticos de versionamento de código para diferentes níveis de senioridade, destacando boas práticas e evolução de responsabilidades.

---

## Versionamento Júnior
- Foco: comandos essenciais, commits atômicos, branches simples (feature/, hotfix/)
- Princípios: pequenas mudanças, mensagens claras, frequência de sincronização

### Boas práticas
- Fazer commits atômicos com escopo único
- Escrever mensagens descritivas e objetivas
- Trabalhar sempre em branch própria (`feature/...` ou `hotfix/...`)
- Sincronizar com `git pull` antes de `git push`

### Exemplos
```bash
# Criar e entrar em uma branch de feature
git checkout -b feature/cadastro-usuario

# Verificar o estado do repositório
git status

# Adicionar alterações ao stage
git add src/forms/cadastro.py

# Commit atômico com mensagem clara
git commit -m "fix: corrige validação de email no formulário de cadastro"

# Sincronizar e enviar alterações
git pull origin feature/cadastro-usuario
git push origin feature/cadastro-usuario
```

---

## Versionamento Pleno
- Foco: padronização (Conventional Commits), histórico linear (rebase), qualidade de PRs
- Princípios: organização de commits, rebase frequente, integração limpa

### Boas práticas
- Usar Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`)
- Preferir `rebase` ao invés de `merge` para manter histórico linear
- Fazer PRs pequenos e objetivo claro
- Resolver conflitos localmente e evitar `--force` (usar `--force-with-lease`)

### Exemplos
```bash
# Mensagem de commit com escopo
git commit -m "feat(authentication): implementa login com OAuth2"

# Atualizar branch de feature com rebase sobre main
git fetch origin
git rebase origin/main

# Resolver conflitos, continuar rebase
# (editar arquivos conflitantes)
git add src/auth/login.py
git rebase --continue

# Enviar alterações com segurança
git push --force-with-lease origin feature/auth-oauth2
```

---

## Versionamento Sênior
- Foco: governança de releases, automação, qualidade contínua, políticas de proteção
- Princípios: versionamento semântico, hooks, CHANGELOG automatizado, proteção de branches

### Boas práticas
- Aplicar Semantic Versioning (SemVer) em tags: `vMAJOR.MINOR.PATCH`
- Usar Git hooks para validação pré-commit (lint, testes)
- Manter `CHANGELOG.md` automaticamente a partir de commits
- Proteger `main` com regras (PR obrigatório, revisão, checks de CI)

### Exemplos
```bash
# Criar tag SemVer anotada para release
git tag -a v1.2.3 -m "Release: novas APIs de pagamento"

git push origin v1.2.3

# Exemplo de hook pré-commit simples (script .git/hooks/pre-commit)
#!/bin/sh
pytest -q || {
  echo "Testes falharam, abortando commit";
  exit 1;
}

# Gerar CHANGELOG com conventional-changelog (exemplo)
# Instalar ferramenta (node): npm i -g conventional-changelog-cli
conventional-changelog -p angular -i CHANGELOG.md -s
```

---

## Boas Práticas Comuns
- `.gitignore` bem configurado para evitar arquivos temporários e segredos
- Padrões de branching coerentes com o time (Git Flow, GitHub Flow)
- Revisão de código via Pull Requests com descrição, escopo e evidências
- Não commitar segredos; usar `.env` e `.env.example`
- Validar com hooks (`pre-commit` Python, linters e testes)

### Exemplos
```bash
# Exemplo de .gitignore essencial
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.log
.env
.DS_Store
EOF

# GitHub Flow (exemplo de ciclo)
git checkout -b feature/nova-api
# commits...
git push -u origin feature/nova-api
# abrir PR no GitHub, solicitar revisão, passar CI
# realizar squash merge e deletar branch
```

---

## Dicas Extras
- Ferramentas úteis: GitLens (VS Code), GitKraken, Sourcetree
- Automatizar qualidade com `pre-commit` (Python) e CI (GitHub Actions)
- Referências:
  - Git: https://git-scm.com/docs
  - Conventional Commits: https://www.conventionalcommits.org/pt-br/v1.0.0/
  - SemVer: https://semver.org/lang/pt-BR/
  - GitHub Flow: https://docs.github.com/en/get-started/quickstart/github-flow

### Comandos úteis por nível
```bash
# Júnior
git status && git add -p && git commit -m "fix: ..."

git checkout -b feature/nome && git push -u origin feature/nome

# Pleno
git fetch origin && git rebase origin/main

git commit -m "feat(modulo): adiciona caso X" && git push --force-with-lease

# Sênior
git tag -a v1.4.0 -m "Release: melhorias"

git push origin v1.4.0 && conventional-changelog -p angular -i CHANGELOG.md -s
```

---

## Conclusão
- Júnior: dominar o básico com segurança e disciplina
- Pleno: elevar a padronização e manter histórico limpo
- Sênior: garantir governança, automação e proteção do processo

Este guia ajuda a evoluir práticas de versionamento com clareza, segurança e colaboração sustentável.

