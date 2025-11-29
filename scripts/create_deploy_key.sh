#!/usr/bin/env bash
# Gera um par de chaves SSH para deploy (chave privada deverá ser adicionada nos Secrets do GitHub)
# Exemplo de uso:
#   scripts/create_deploy_key.sh deploy_key
# Saída:
#   - deploy_key (private)
#   - deploy_key.pub (public)

set -euo pipefail

OUT_PREFIX=${1:-deploy_key}

if [ -f "${OUT_PREFIX}" ] || [ -f "${OUT_PREFIX}.pub" ]; then
  echo "Arquivo ${OUT_PREFIX} ou ${OUT_PREFIX}.pub já existe. Remova ou escolha outro nome." >&2
  exit 1
fi

echo "Gerando par de chaves: ${OUT_PREFIX} e ${OUT_PREFIX}.pub"
ssh-keygen -t ed25519 -C "deploy@project_automation" -f "${OUT_PREFIX}" -N ""
chmod 600 "${OUT_PREFIX}"

echo "--- Chave pública (copie para ~/.ssh/authorized_keys no servidor) ---"
cat "${OUT_PREFIX}.pub"
echo "--- Arquivo privado salvo em ${OUT_PREFIX} (mantenha seguro) ---"

echo "Para adicionar o segredo no GitHub (Actions):
1) Abra Settings → Secrets and variables → Actions → New repository secret
2) Nome: SSH_PRIVATE_KEY
3) Valor: conteúdo do arquivo ${OUT_PREFIX} (copie/cole)
" >&2

exit 0
