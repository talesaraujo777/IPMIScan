# IPMI Scan

# IPMI - Interface Inteligente de Gerenciamento de Plataforma

Web app em Flask para descobrir interfaces IPMI na rede usando RMCP/ASF em UDP 623.

## Requisitos

- Python 3
- Dependências Python (requirements.txt)

## Passo a passo

`cd /caminho/IPMIScan`

`python3 -m venv .venv`

Windows: `.\.venv\Scripts\activate`
                
Linux: `source .venv/bin/activate`

`pip install -r requirements.txt`

`python3 app.py`

Abra: 'http://localhost:5000'


## Docker

- Requisitos: Docker desktop

`cd /caminho/IPMIScan`

`docker compose up -d --build`

Abra: 'http://localhost:5000'

Detalhes:

- a imagem usa 'python:3.13-slim'
- os presets são persistidos em './data/presets.json' no diretório raiz do projeto
- para ver os logs: 'docker compose logs -f'

## Como funciona

- Envia pacotes RMCP/ASF para UDP 623 e aguarda resposta.
- Lista os resultados em tabela (serviço e IP).

## Observações

- O app limita varreduras a 4096 hosts por segurança.
- Campos do scan: IP inicial, IP final e máscara de rede (calculada automaticamente pelo front-end).

<img width="1365" height="767" alt="Captura de tela 2026-04-14 085645" src="https://github.com/user-attachments/assets/5a7a0fe3-2172-4e22-86cc-3bb0ee5b6432" />



