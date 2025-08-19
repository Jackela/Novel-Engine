#!/usr/bin/env python3
"""
API服务器调试脚本
"""

import os
import sys
import time
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_startup():
    """调试启动过程"""
    print("=== API服务器调试 ===")
    
    # 1. 检查依赖
    print("1. 检查依赖...")
    missing = []
    deps = ['fastapi', 'uvicorn', 'google.generativeai']
    
    for dep in deps:
        try:
            __import__(dep)
            print(f"  OK {dep}")
        except ImportError:
            print(f"  FAIL {dep}")
            missing.append(dep)
    
    if missing:
        print(f"缺失依赖: {missing}")
        return False
    
    # 2. 检查环境变量
    print("2. 检查环境变量...")
    gemini_key = os.getenv('GEMINI_API_KEY')
    if gemini_key:
        print(f"  OK GEMINI_API_KEY (length: {len(gemini_key)})")
    else:
        print("  FAIL GEMINI_API_KEY not set")
    
    # 3. 检查配置文件
    print("3. 检查配置文件...")
    try:
        from config_loader import get_config
        config = get_config()
        print("  OK config loaded")
    except Exception as e:
        print(f"  FAIL config load: {e}")
        return False
    
    # 4. 检查字符目录
    print("4. 检查字符目录...")
    chars_dir = "characters"
    if os.path.isdir(chars_dir):
        chars = [d for d in os.listdir(chars_dir) if os.path.isdir(os.path.join(chars_dir, d))]
        print(f"  OK found {len(chars)} characters: {chars}")
    else:
        print(f"  WARN characters dir missing: {chars_dir}")
        os.makedirs(chars_dir, exist_ok=True)
        print(f"  OK created dir: {chars_dir}")
    
    # 5. 测试核心组件
    print("5. 测试核心组件...")
    try:
        from src.event_bus import EventBus
        from character_factory import CharacterFactory
        
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        print("  OK EventBus and CharacterFactory")
    except Exception as e:
        print(f"  FAIL component load: {e}")
        return False
    
    # 6. 启动最小化API
    print("6. 启动最小化API服务器...")
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn
        
        app = FastAPI(title="Debug API")
        
        @app.get("/")
        def root():
            return {"message": "Debug API running"}
        
        @app.get("/health")
        def health():
            return {
                "status": "healthy",
                "gemini_key_set": bool(os.getenv('GEMINI_API_KEY')),
                "timestamp": time.time()
            }
        
        print("  Starting server on http://127.0.0.1:8001")
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
        
    except Exception as e:
        print(f"  FAIL startup: {e}")
        return False

if __name__ == "__main__":
    debug_startup()