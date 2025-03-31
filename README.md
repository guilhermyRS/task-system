# Gerenciador de Tarefas

Um aplicativo web para gerenciamento de tarefas, listas e subtarefas, desenvolvido com Flask.

## Características

- Autenticação de usuários (registro, login, perfil)
- Criação e gerenciamento de listas de tarefas
- Tarefas com subtarefas e etapas
- Acompanhamento de progresso visual
- Mensagens motivacionais
- Interface responsiva

## Tecnologias Utilizadas

- Flask (Backend)
- SQLAlchemy (ORM)
- HTML, CSS, JavaScript (Frontend)
- SQLite (Banco de dados)

## Implantação na Vercel

Este projeto está configurado para ser implantado na Vercel. Para implantar:

1. Crie uma conta na [Vercel](https://vercel.com)
2. Instale a CLI da Vercel: `npm i -g vercel`
3. Faça login na CLI: `vercel login`
4. No diretório do projeto, execute: `vercel`
5. Siga as instruções para concluir a implantação

## Variáveis de Ambiente

Configure as seguintes variáveis de ambiente na Vercel:

- `SECRET_KEY`: Chave secreta para o Flask
- `DATABASE_URL` (opcional): URL para um banco de dados externo

## Desenvolvimento Local

Para executar o projeto localmente:

1. Clone o repositório
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Instale as dependências: `pip install -r requirements.txt`
5. Execute o aplicativo: `python app.py`
6. Acesse http://localhost:5000 no navegador