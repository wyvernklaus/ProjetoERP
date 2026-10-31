# ProjetoERP

Sistema ERP (Enterprise Resource Planning) desenvolvido em Python com FastAPI, 
com autenticação JWT, controle de acesso e interface web servida via Jinja2.

##  Sobre o projeto

O ProjetoERP é uma aplicação web para gestão empresarial que centraliza 
módulos de negócio em uma única plataforma. O sistema conta com autenticação 
de usuários, controle de permissões por abas/funcionalidades e registro de 
auditoria das ações realizadas.

##  Tecnologias utilizadas

| Camada | Tecnologia |
| :--- | :--- |
| **Linguagem** | Python 3.x |
| **Framework Web** | FastAPI |
| **Banco de dados** | SQLite (via SQLAlchemy) |
| **Autenticação** | JWT + bcrypt |
| **Templates** | Jinja2 |
| **Frontend** | HTML, CSS, JavaScript |

##  Estrutura do projeto
ProjetoERP/
├── core/ # Lógica de negócio e módulos internos
├── routers/ # Rotas da API e endpoints
├── Templates/ # Templates HTML (Jinja2)
├── static/ # Arquivos estáticos (CSS, JS, imagens)
├── uploads/ # Arquivos enviados pelos usuários
├── Legado/ # Código de versões anteriores (referência)
├── main.py # Ponto de entrada da aplicação
├── requirements.txt # Dependências do projeto
├── iniciar_business.bat # Script de inicialização (Windows)
└── banco.db # Banco de dados SQLite (gerado em runtime)

text

## 🚀 Como executar o projeto

### Pré-requisitos

- Python 3.10 ou superior
- pip

### Passo a passo

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/wyvernklaus/ProjetoERP.git
   cd ProjetoERP
Crie e ative um ambiente virtual:

## bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
Instale as dependências:

## bash
pip install -r requirements.txt
Execute a aplicação:

bash
# Opção 1: Script de inicialização (Windows)
iniciar_business.bat

# Opção 2: Comando direto
uvicorn main:app --reload
Acesse no navegador:

text
http://localhost:1687

## Autenticação
O sistema utiliza autenticação via JWT armazenado em cookies httponly.
O fluxo básico é:

O usuário faz login com credenciais.

O servidor valida e retorna um token JWT.

O token é enviado em todas as requisições subsequentes via cookie.

O acesso a cada módulo é controlado por permissões configuradas.

## Funcionalidades
Seção a ser preenchida — liste aqui os módulos reais do ERP.

□ Módulo 1
□ Módulo 2
□ Módulo 3

## Roadmap
□ Melhorar cobertura de testes
□ Implementar migrações com Alembic
□ Adicionar documentação da API (Swagger/OpenAPI já disponível em /docs)
□ Containerização com Docker

 
 ## Licença e Direitos Autorais
Copyright (c) 2026 wyvernklaus. Todos os Direitos Reservados.

Este repositório e todo o seu conteúdo (código-fonte, documentação, assets e
quaisquer outros arquivos) são propriedade exclusiva do autor.

Nenhuma licença, expressa ou implícita, é concedida a qualquer pessoa para
usar, copiar, modificar, mesclar, publicar, distribuir, sublicenciar ou
vender cópias deste software ou de partes dele.

A visualização e o "fork" técnico deste repositório na plataforma GitHub são
permitidos exclusivamente pelos Termos de Serviço da própria plataforma. Isso
não constitui permissão para qualquer outro uso do código.

Para quaisquer dúvidas sobre permissões de uso, entre em contato com o autor.
