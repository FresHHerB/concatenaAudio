from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse
from typing import List, Optional
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
async def concatenate_audio(request: Request, files: Optional[List[UploadFile]] = File(None)):
    """
    Concatena múltiplos arquivos de áudio na ordem recebida
    VERSÃO COM DEBUG PARA N8N - ACEITA ARRAY DE ARQUIVOS
    """
    
    # DEBUG: Log da requisição recebida
    print(f"=== DEBUG REQUEST ===")
    print(f"Content-Type: {request.headers.get('content-type', 'Not set')}")
    
    # Se files está vazio, tentar form-data manual
    if not files:
        print("Files vazio, tentando form-data manual...")
        try:
            form = await request.form()
            print(f"Form keys: {list(form.keys())}")
            
            # Coletar arquivos do form-data
            files = []
            
            # Tentar coletar arquivos de diferentes formas
            for key, value in form.items():
                print(f"Form field: {key}, type: {type(value)}")
                if hasattr(value, 'filename') and hasattr(value, 'file'):
                    print(f"Encontrado arquivo: {value.filename}, content_type: {getattr(value, 'content_type', 'unknown')}")
                    files.append(value)
            
            # Se não encontrou, tentar por prefix
            if not files:
                # Coletar campos que começam com "file_" ou "files"
                file_keys = [k for k in form.keys() if k.startswith(('file_', 'files'))]
                print(f"Chaves de arquivo encontradas: {file_keys}")
                
                # Ordenar para manter sequência
                file_keys.sort(key=lambda x: int(x.split('_')[-1]) if '_' in x and x.split('_')[-1].isdigit() else 0)
                
                for key in file_keys:
                    value = form[key]
                    if hasattr(value, 'filename') and hasattr(value, 'file'):
                        print(f"Arquivo ordenado: {key} -> {value.filename}")
                        files.append(value)
                        
        except Exception as e:
            print(f"Erro ao processar form-data: {e}")
            raise HTTPException(status_code=400, detail=f"Erro ao processar form-data: {str(e)}")
    
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    
    print(f"Arquivos recebidos: {len(files)}")
    for i, file in enumerate(files):
        content = await file.read()
        print(f"Arquivo {i}: {file.filename}, size: {len(content)} bytes")
        await file.seek(0)  # Reset file pointer
    
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Envie pelo menos 2 arquivos para concatenação")
    
    # Gerar ID único para esta operação
    operation_id = str(uuid.uuid4())
    temp_files = []
    
    try:
        # Salvar arquivos temporariamente
        for i, file in enumerate(files):
            print(f"Processando arquivo {i}: {file.filename}")
            
            # Extensão do arquivo
            file_extension = Path(file.filename).suffix if file.filename else '.mp3'
            temp_file_path = TEMP_DIR / f"{operation_id}_input_{i:03d}{file_extension}"
            
            # Salvar arquivo
            content = await file.read()
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content)
            
            print(f"Arquivo salvo: {temp_file_path}, size: {len(content)} bytes")
            temp_files.append(str(temp_file_path))
        
        # Criar arquivo de lista para FFmpeg
        list_file_path = TEMP_DIR / f"{operation_id}_list.txt"
        with open(list_file_path, "w") as list_file:
            for temp_file in temp_files:
                # Escapar aspas simples no nome do arquivo
                escaped_path = temp_file.replace("'", "'\"'\"'")
                list_file.write(f"file '{escaped_path}'\n")
        
        print(f"Lista de arquivos criada: {list_file_path}")
        
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
        
        print(f"Executando FFmpeg: {' '.join(ffmpeg_command)}")
        
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
            
            print(f"Executando FFmpeg (reencoding): {' '.join(ffmpeg_command_reencode)}")
            
            result = subprocess.run(
                ffmpeg_command_reencode,
                capture_output=True,
                text=True,
                timeout=300
            )
        
        if result.returncode != 0:
            print(f"FFmpeg falhou: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro no FFmpeg: {result.stderr}"
            )
        
        if not output_file_path.exists():
            raise HTTPException(status_code=500, detail="Arquivo de saída não foi criado")
        
        print(f"Arquivo de saída criado: {output_file_path}, size: {output_file_path.stat().st_size} bytes")
        
        # Retornar arquivo
        def cleanup_after_response():
            """Cleanup após enviar resposta"""
            print("Limpando arquivos temporários...")
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
        print(f"Erro interno: {str(e)}")
        cleanup_files(temp_files + [str(list_file_path)])
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)
