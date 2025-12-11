#!/usr/bin/env python3
"""
모델 파일 다운로드 스크립트
GitHub Release 또는 외부 저장소에서 모델 파일을 다운로드합니다.
"""
import os
import sys
import requests
from pathlib import Path

# 모델 파일 정보
MODEL_FILES = {
    "best_mcp_lstm_model.h5": {
        "url": "https://github.com/MCP-AI-Ops/mcp_core/releases/download/v1.0.0-models/best_mcp_lstm_model.h5",
        "size_mb": 0.25,
        "required": True,
    },
    "best_mcp_lstm_checkpoint.h5": {
        "url": "https://github.com/MCP-AI-Ops/mcp_core/releases/download/v1.0.0-models/best_mcp_lstm_checkpoint.h5",
        "size_mb": 0.66,
        "required": False,
    },
    "mcp_model_metadata.pkl": {
        "url": "https://github.com/MCP-AI-Ops/mcp_core/releases/download/v1.0.0-models/mcp_model_metadata.pkl",
        "size_mb": 0.01,
        "required": True,
    },
}

def download_file(url: str, dest_path: Path) -> bool:
    """파일 다운로드"""
    try:
        print(f"다운로드 중: {dest_path.name}...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ 완료: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return True
    except Exception as e:
        print(f"❌ 실패: {dest_path.name} - {e}")
        return False

def main():
    """메인 실행"""
    models_dir = Path(__file__).parent.parent / "models"
    
    print("=" * 60)
    print("MCP 모델 파일 다운로드")
    print("=" * 60)
    
    # 이미 존재하는 파일 체크
    existing_files = []
    missing_files = []
    
    for filename in MODEL_FILES:
        file_path = models_dir / filename
        if file_path.exists():
            existing_files.append(filename)
        else:
            missing_files.append(filename)
    
    if existing_files:
        print(f"\n✅ 이미 존재하는 파일 ({len(existing_files)}개):")
        for filename in existing_files:
            print(f"   - {filename}")
    
    if not missing_files:
        print("\n🎉 모든 모델 파일이 이미 존재합니다!")
        return 0
    
    print(f"\n📦 다운로드할 파일 ({len(missing_files)}개):")
    for filename in missing_files:
        info = MODEL_FILES[filename]
        print(f"   - {filename} ({info['size_mb']} MB)")
    
    total_size = sum(MODEL_FILES[f]['size_mb'] for f in missing_files)
    print(f"\n💾 총 다운로드 크기: {total_size:.2f} MB")
    
    # 다운로드 시작
    print("\n" + "=" * 60)
    success_count = 0
    
    for filename in missing_files:
        info = MODEL_FILES[filename]
        file_path = models_dir / filename
        
        if download_file(info['url'], file_path):
            success_count += 1
        elif info['required']:
            print(f"\n❌ 필수 파일 다운로드 실패: {filename}")
            return 1
    
    print("\n" + "=" * 60)
    print(f"✅ 다운로드 완료: {success_count}/{len(missing_files)} 파일")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
