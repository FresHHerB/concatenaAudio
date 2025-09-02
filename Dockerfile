FROM python:3.11-slim

# Instalar dependências do sistema incluindo FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY main.py .

# Criar diretório temporário para processamento
RUN mkdir -p /tmp/audio_processing

# Expor porta
EXPOSE 8999

# Comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8999"]