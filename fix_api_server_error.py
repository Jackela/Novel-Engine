#!/usr/bin/env python3
"""
修复API服务器错误
"""

import os
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def diagnose_issue():
    """诊断API服务器问题"""
    print("=== 诊断API服务器问题 ===")
    
    # 1. 检查GEMINI_API_KEY设置
    print("1. 检查环境变量...")
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key or gemini_key == 'your_key_here':
        print("PROBLEM: GEMINI_API_KEY 未正确设置")
        print("需要设置真实的Gemini API密钥")
        return False
    else:
        print(f"OK: GEMINI_API_KEY 已设置 (length: {len(gemini_key)})")
    
    # 2. 测试直接的Gemini API调用
    print("2. 测试Gemini API连接...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello")
        
        if response and response.text:
            print("OK: Gemini API连接正常")
        else:
            print("PROBLEM: Gemini API无响应")
            return False
    except Exception as e:
        print(f"PROBLEM: Gemini API错误: {e}")
        return False
    
    # 3. 检查配置加载
    print("3. 检查配置文件...")
    try:
        from config_loader import get_config
        config = get_config()
        print("OK: 配置加载成功")
    except Exception as e:
        print(f"PROBLEM: 配置加载失败: {e}")
        return False
    
    # 4. 检查src模块导入
    print("4. 检查src模块...")
    try:
        from src.persona_agent import _validate_gemini_api_key, _make_gemini_api_request
        print("OK: persona_agent模块导入成功")
        
        # 测试API密钥验证
        if _validate_gemini_api_key(gemini_key):
            print("OK: API密钥验证通过")
        else:
            print("PROBLEM: API密钥验证失败")
            return False
            
    except Exception as e:
        print(f"PROBLEM: src模块导入失败: {e}")
        return False
    
    print("✓ 所有检查通过")
    return True

def create_fixed_api_server():
    """创建修复版本的API服务器"""
    print("创建修复版本的API服务器...")
    
    fixed_code = '''#!/usr/bin/env python3
"""
修复版API服务器
"""

import os
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 验证环境变量
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY or GEMINI_API_KEY == 'your_key_here':
    logger.error("GEMINI_API_KEY not properly set")
    exit(1)

app = FastAPI(title="Fixed StoryForge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    timestamp: float
    gemini_key_set: bool

class CharactersResponse(BaseModel):
    characters: List[str]

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径健康检查"""
    return {"message": "Fixed StoryForge API is running"}

@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    try:
        # 测试Gemini API连接
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("test")
        
        gemini_working = bool(response and response.text)
        
        return HealthResponse(
            status="healthy" if gemini_working else "degraded",
            timestamp=time.time(),
            gemini_key_set=bool(GEMINI_API_KEY)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=time.time(),
            gemini_key_set=bool(GEMINI_API_KEY)
        )

@app.get("/characters", response_model=CharactersResponse)
async def get_characters():
    """获取角色列表"""
    try:
        characters_dir = "characters"
        
        if not os.path.isdir(characters_dir):
            os.makedirs(characters_dir, exist_ok=True)
            return CharactersResponse(characters=[])
        
        characters = []
        for item in os.listdir(characters_dir):
            if os.path.isdir(os.path.join(characters_dir, item)):
                characters.append(item)
        
        return CharactersResponse(characters=sorted(characters))
        
    except Exception as e:
        logger.error(f"Get characters failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-story")
async def test_story(prompt: str = "Generate a short story"):
    """测试故事生成"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Write a short story: {prompt}")
        
        if response and response.text:
            return {"story": response.text, "status": "success"}
        else:
            return {"story": "", "status": "no_response"}
            
    except Exception as e:
        logger.error(f"Story generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")
'''
    
    with open('fixed_api_server.py', 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    print("✓ 修复版API服务器已创建: fixed_api_server.py")

def main():
    """主函数"""
    if diagnose_issue():
        create_fixed_api_server()
        print("\\n修复完成。运行: python fixed_api_server.py")
        return True
    else:
        print("\\n发现问题，需要手动修复")
        return False

if __name__ == "__main__":
    main()