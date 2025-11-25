# Guia Prático de Git e GitHub

Este guia consolida os comandos essenciais para trabalhar com versionamento em equipes corporativas, com exemplos de uso e boas práticas para fluxos de colaboração.

## 1. Configuração Básica

- `git config --global user.name "Seu Nome"`
- `git config --global user.email "seu@email.com"`
- `git config --global core.editor "code --wait"` (opcional)
- `git config --global pull.rebase false` (ou `true` se preferir rebase)
- `git config --global init.defaultBranch main`
- `git config --global commit.gpgSign true` (se usar assinatura GPG)

## 2. Iniciar e Clonar Repositórios

- `git init`
- `git clone ${url_do_repositório}`
- `git remote add origin ${url_do_repositório}`
- `git remote -v`

## 3. Fluxo de Trabalho Diário

- `git status`
- `git add ${arquivo_ou_pasta}`
- `git commit -m "mensagem descritiva"`
- `git push origin ${branch}`
- `git pull origin ${branch}`
- Dicas:
  - `git add -p` para selecionar trechos
  - `git commit -s` para assinar (DCO)

## 4. Gerenciamento de Branches

- `git branch`
- `git branch ${nome_da_branch}`
- `git checkout ${branch}`
- `git checkout -b ${nova_branch}`
- `git merge ${branch}`
- `git branch -d ${branch}` (local)
- `git push origin --delete ${branch}` (remota)
- Alternativas modernas:
  - `git switch -c ${nova_branch}` (criar e trocar)
  - `git switch ${branch}` (trocar)

## 5. Resolução de Conflitos

- `git diff`
- `git mergetool`
- `git rebase ${branch}`
- Passos comuns:
  1. `git fetch origin`
  2. `git rebase origin/main`
  3. Resolver conflitos, `git add`, `git rebase --continue`
  4. `git push --force-with-lease` (se necessário, com segurança)

## 6. Histórico e Inspeção

- `git log` (use `--oneline --graph --decorate`)
- `git show ${commit_id}`
- `git blame ${arquivo}`
- `git reflog` (recuperar referências perdidas)

## 7. Trabalho em Equipe

- `git fetch`
- `git pull --rebase`
- `git cherry-pick ${commit_id}`
- `git stash`
- `git stash apply` (ou `git stash pop`)
- `git fetch --prune` (limpar referências remotas obsoletas)

## 8. Tags e Releases

- `git tag ${nome_da_tag}`
- `git tag -a ${nome_da_tag} -m "mensagem"` (anotada)
- `git push origin ${tag}`
- `git push origin --tags`

## 9. Desfazer Alterações

- `git reset ${arquivo}` (tira do stage)
- `git restore --staged ${arquivo}` (alternativa moderna)
- `git reset --hard ${commit_id}` (cuidado!)
- `git revert ${commit_id}` (gera novo commit inverso)
- `git restore ${arquivo}` (restaurar conteúdo)

## 10. Fluxo Corporativo Recomendado (Exemplo)

1. Criar branch de feature: `git switch -c feature/minha-feature`
2. Commits pequenos e claros: `git add -p && git commit -m "feat: add X"`
3. Sincronizar periodicamente: `git fetch origin && git rebase origin/main`
4. Push com upstream: `git push -u origin feature/minha-feature`
5. Abrir Pull Request e solicitar revisão (GitHub)
6. Após aprovação, merge (preferir squash ou rebase + FF)

## 11. Mensagens de Commit Claras

- Recomenda-se o padrão Conventional Commits:
  - `feat: descrição da funcionalidade`
  - `fix: correção de bug`
  - `docs: atualização de documentação`
  - `refactor: refatoração sem mudança de comportamento`
  - `test: adiciona/ajusta testes`
  - `chore: tarefas diversas`
- Inclua contexto e impacto; evite mensagens vagas.

## 12. Boas Práticas

- Sempre fazer `git pull` (ou `git fetch` + `rebase`) antes de `git push`
- Escrever mensagens de commit claras e descritivas
- Criar branches específicas para cada feature/fix
- Revisar código via Pull Requests e aprovações
- Resolver conflitos localmente antes de fazer `push`
- Evitar `--force`; se necessário, use `--force-with-lease`
- Proteja a branch `main` com regras (require PR, checks, reviews)
- Não commitar segredos; use `.env` e `.env.example`
- Padronizar hooks com `pre-commit` (lint, testes)

## 13. Comandos Úteis Adicionais

- `git clean -fd` (remove arquivos não rastreados)
- `git describe --tags` (identificar versão/tag mais próxima)
- `git shortlog -sne` (contribuidores)
- `git bisect` (isolar commit que introduziu bug)
- `git sparse-checkout` (clonar parcialmente)

## 14. Resolução de Problemas (Debug)

- Conflitos: use `git status` para ver arquivos, `git diff` para contexto
- Rebase travado: `git rebase --abort` e recomece limpo
- Perdi commits: `git reflog` ajuda a recuperar
- Divergências remotas: `git fetch --all --prune` e compare

---

### Anexos Rápidos (Cheat Sheet)

```bash
# Definir nome do autor dos commits
git config --global user.name "Seu Nome"

# Definir e-mail do autor dos commits
git config --global user.email "seu@email.com"

# Iniciar repositório vazio no diretório atual
git init

# Clonar repositório remoto para máquina local
git clone ${url}

# Registrar origem remota do repositório local
git remote add origin ${url}

# Ver estado de alterações, staged e não rastreados
git status

# Adicionar arquivo ou pasta ao stage
git add ${arquivo}

# Criar commit com mensagem descritiva
git commit -m "mensagem"

# Atualizar branch local a partir do remoto
git pull origin ${branch}

# Enviar branch local para o repositório remoto
git push origin ${branch}

# Criar e trocar para nova branch de feature
git switch -c feature/nome

# Trocar para uma branch existente
git switch ${branch}

# Mesclar branch alvo na branch atual
git merge ${branch}

# Apagar branch local já mesclada
git branch -d ${branch}

# Buscar do remoto e preparar integração
git fetch origin

# Rebasear branch atual no main remoto
git rebase origin/main

# Abrir ferramenta gráfica para resolver conflitos
git mergetool

# Mostrar histórico resumido com gráfico e decorações
git log --oneline --graph --decorate

# Inspecionar detalhes de um commit específico
git show ${commit}

# Mostrar autoria linha a linha do arquivo
git blame ${arquivo}

# Sincronizar referências remotas e remover obsoletas
git fetch --prune

# Atualizar branch com rebase ao puxar
git pull --rebase

# Aplicar commit específico sobre a branch atual
git cherry-pick ${commit}

# Guardar alterações locais temporariamente
git stash

# Reaplicar alterações guardadas do stash
git stash apply

# Criar tag anotada para release
git tag -a v1.2.0 -m "release 1.2.0"

# Enviar tag específica ao remoto
git push origin v1.2.0

# Tirar arquivo do stage (desfazer add)
git restore --staged ${arquivo}

# Restaurar conteúdo do arquivo ao último commit
git restore ${arquivo}

# Redefinir branch para commit específico (destrutivo)
git reset --hard ${commit}

# Criar commit que desfaz mudanças de um commit
git revert ${commit}
```

> Dica: configure Protections no GitHub (Branch protection rules), exigindo PRs, revisões, e checks de CI para `main`.
