from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from typing import List
import os
import tempfile
import subprocess
import uuid
import asyncio
from pathlib import Path
import shutil

app = FastAPI(title="Audio Concatenation Service", version="1.0.0")

# Diretório temporário para processamento
TEMP_DIR = Path("/tmp/audio_processing")
TEMP_DIR.mkdir(exist_ok=True)


def cleanup_files(file_paths: List[str]):
    """Remove arquivos temporários"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Erro ao remover arquivo {file_path}: {e}")


def check_ffmpeg():
    """Verifica se FFmpeg está instalado"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@app.on_event("startup")
async def startup_event():
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg não encontrado. Instale FFmpeg para usar esta API.")
    print("Audio Concatenation Service iniciado com sucesso!")


@app.get("/")
async def root():
    return {
        "message": "Audio Concatenation Service",
        "endpoint": "/fullAudio",
        "method": "POST",
        "description": "Envie múltiplos arquivos de áudio para concatenação"
    }


@app.get("/health")
async def health_check():
    ffmpeg_available = check_ffmpeg()
    return {
        "status": "healthy" if ffmpeg_available else "unhealthy",
        "ffmpeg": "available" if ffmpeg_available else "not available"
    }


@app.post("/fullAudio")
async def concatenate_audio(files: List[UploadFile] = File(...)):
    """
    Concatena múltiplos arquivos de áudio na ordem recebida
    """
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Envie pelo menos 2 arquivos para concatenação")

    # Gerar ID único para esta operação
    operation_id = str(uuid.uuid4())
    temp_files = []

    try:
        # Salvar arquivos temporariamente
        for i, file in enumerate(files):
            if not file.content_type or not file.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail=f"Arquivo {i + 1} não é um arquivo de áudio válido")

            # Extensão do arquivo
            file_extension = Path(file.filename).suffix if file.filename else '.mp3'
            temp_file_path = TEMP_DIR / f"{operation_id}_input_{i:03d}{file_extension}"

            # Salvar arquivo
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            temp_files.append(str(temp_file_path))

        # Criar arquivo de lista para FFmpeg
        list_file_path = TEMP_DIR / f"{operation_id}_list.txt"
        with open(list_file_path, "w") as list_file:
            for temp_file in temp_files:
                # Escapar aspas simples no nome do arquivo
                escaped_path = temp_file.replace("'", "'\"'\"'")
                list_file.write(f"file '{escaped_path}'\n")

        # Arquivo de saída
        output_file_path = TEMP_DIR / f"{operation_id}_output.mp3"

        # Comando FFmpeg para concatenação sem reencoding (preserva qualidade)
        ffmpeg_command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file_path),
            "-c", "copy",  # Copia streams sem reencoding
            "-y",  # Sobrescrever arquivo de saída
            str(output_file_path)
        ]

        # Executar FFmpeg
        result = subprocess.run(
            ffmpeg_command,
            capture_output=True,
            text=True,
            timeout=300  # Timeout de 5 minutos
        )

        if result.returncode != 0:
            # Se copy falhar, tentar com reencoding
            print(f"Copy mode falhou, tentando com reencoding: {result.stderr}")

            ffmpeg_command_reencode = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file_path),
                "-acodec", "libmp3lame",
                "-b:a", "320k",  # Alta qualidade
                "-ar", "44100",  # Sample rate
                "-y",
                str(output_file_path)
            ]

            result = subprocess.run(
                ffmpeg_command_reencode,
                capture_output=True,
                text=True,
                timeout=300
            )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Erro no FFmpeg: {result.stderr}"
            )

        if not output_file_path.exists():
            raise HTTPException(status_code=500, detail="Arquivo de saída não foi criado")

        # Retornar arquivo
        def cleanup_after_response():
            """Cleanup após enviar resposta"""
            cleanup_files(temp_files + [str(list_file_path), str(output_file_path)])

        return FileResponse(
            path=str(output_file_path),
            media_type='audio/mpeg',
            filename=f'concatenated_audio_{operation_id[:8]}.mp3',
            background=cleanup_after_response
        )

    except asyncio.TimeoutError:
        cleanup_files(temp_files + [str(list_file_path)])
        raise HTTPException(status_code=408, detail="Timeout no processamento do áudio")

    except Exception as e:
        cleanup_files(temp_files + [str(list_file_path)])
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8999)
