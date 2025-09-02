\# Audio Concatenation API



API FastAPI para concatenar múltiplos arquivos de áudio usando FFmpeg sem perda de qualidade.



\## Funcionalidades



\- Concatena múltiplos arquivos de áudio na ordem recebida

\- Preserva qualidade original (sem reencoding quando possível)

\- Suporte a vários formatos de áudio (MP3, WAV, M4A, etc.)

\- Limpeza automática de arquivos temporários

\- Health check endpoint

\- Container Docker pronto para produção



\## Endpoints



\### `POST /fullAudio`

Concatena múltiplos arquivos de áudio.



\*\*Parâmetros:\*\*

\- `files`: Lista de arquivos de áudio (form-data)



\*\*Resposta:\*\*

\- Arquivo MP3 concatenado

\- Header: `Content-Type: audio/mpeg`



\### `GET /health`

Verifica status da API e disponibilidade do FFmpeg.



\### `GET /`

Informações sobre a API.



\## Instalação Local



\### Pré-requisitos

\- Python 3.11+

\- FFmpeg instalado



\### 1. Clonar repositório

```bash

git clone <seu-repositorio>

cd audio-concatenation-api

```



\### 2. Instalar dependências

```bash

pip install -r requirements.txt

```



\### 3. Executar

```bash

python main.py

```



A API estará disponível em `http://localhost:8999`



\## Deploy com Docker



\### 1. Build da imagem

```bash

docker build -t audio-api .

```



\### 2. Executar container

```bash

docker run -p 8999:8999 audio-api

```



\### 3. Ou usar Docker Compose

```bash

docker-compose up -d

```



\## Deploy no EasyPanel



\### 1. Criar novo serviço

1\. Acesse seu painel EasyPanel

2\. Clique em "Create Service"

3\. Selecione "Source Code"



\### 2. Configurar repositório

\- \*\*Repository URL\*\*: URL do seu repositório GitHub

\- \*\*Branch\*\*: main

\- \*\*Build Command\*\*: `docker build -t audio-api .`

\- \*\*Start Command\*\*: `uvicorn main:app --host 0.0.0.0 --port 8999`



\### 3. Configurar porta

\- \*\*Port\*\*: 8999

\- \*\*Protocol\*\*: HTTP



\### 4. Variáveis de ambiente (opcional)

```

PYTHONUNBUFFERED=1

```



\### 5. Deploy

Clique em "Deploy" e aguarde a conclusão.



\## Uso da API



\### Exemplo com cURL

```bash

curl -X POST "http://localhost:8999/fullAudio" \\

&nbsp; -H "Content-Type: multipart/form-data" \\

&nbsp; -F "files=@audio1.mp3" \\

&nbsp; -F "files=@audio2.mp3" \\

&nbsp; -F "files=@audio3.mp3" \\

&nbsp; --output resultado.mp3

```



\### Exemplo com Python

```python

import requests



url = "http://localhost:8999/fullAudio"

files = \[

&nbsp;   ('files', ('audio1.mp3', open('audio1.mp3', 'rb'), 'audio/mpeg')),

&nbsp;   ('files', ('audio2.mp3', open('audio2.mp3', 'rb'), 'audio/mpeg')),

&nbsp;   ('files', ('audio3.mp3', open('audio3.mp3', 'rb'), 'audio/mpeg'))

]



response = requests.post(url, files=files)



if response.status\_code == 200:

&nbsp;   with open('resultado.mp3', 'wb') as f:

&nbsp;       f.write(response.content)

&nbsp;   print("Áudio concatenado com sucesso!")

else:

&nbsp;   print(f"Erro: {response.status\_code} - {response.text}")

```



\### Exemplo no n8n

```javascript

// No nó HTTP Request do n8n

// Method: POST

// URL: http://seu-servidor:8999/fullAudio

// Body: Form-Data

// Anexar arquivos de áudio na propriedade 'files'

```



\## Estrutura do Projeto



```

audio-concatenation-api/

├── main.py              # Aplicação FastAPI

├── requirements.txt     # Dependências Python

├── Dockerfile          # Container Docker

├── docker-compose.yml  # Configuração Docker Compose

├── .gitignore         # Arquivos ignorados pelo Git

└── README.md          # Este arquivo

```



\## Logs e Debugging



Para visualizar logs em tempo real:

```bash

docker-compose logs -f audio-api

```



Para debug local:

```bash

uvicorn main:app --host 0.0.0.0 --port 8999 --reload --log-level debug

```



\## Limitações



\- Timeout de 5 minutos por operação

\- Arquivos são processados na memória (considere o tamanho)

\- Requer FFmpeg instalado no sistema/container



\## Tecnologias Utilizadas



\- \*\*FastAPI\*\*: Framework web moderno e rápido

\- \*\*FFmpeg\*\*: Processamento de áudio profissional

\- \*\*Docker\*\*: Containerização

\- \*\*Python 3.11\*\*: Linguagem de programação



\## Suporte



Para problemas ou sugestões, abra uma issue no repositório GitHub.



\## Licença



MIT License

