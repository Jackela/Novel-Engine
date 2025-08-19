#!/usr/bin/env python3
"""
最小化API服务器用于测试
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

# 检查环境变量
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

app = FastAPI(title="Minimal Test API", version="1.0.0")

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
    api_version: str

class CharactersResponse(BaseModel):
    characters: List[str]

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Minimal Test API is running", "status": "ok"}

@app.get("/health")
async def health():
    """健康检查"""
    try:
        gemini_available = False
        
        if GEMINI_API_KEY and GEMINI_API_KEY != 'your_key_here':
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("hello")
                
                gemini_available = bool(response and response.text)
            except Exception as e:
                logger.warning(f"Gemini API test failed: {e}")
                gemini_available = False
        
        return {
            "status": "healthy" if gemini_available else "limited",
            "timestamp": time.time(),
            "gemini_key_set": bool(GEMINI_API_KEY and GEMINI_API_KEY != 'your_key_here'),
            "gemini_available": gemini_available,
            "api_version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "timestamp": time.time(),
            "gemini_key_set": bool(GEMINI_API_KEY),
            "error": str(e),
            "api_version": "1.0.0"
        }

@app.get("/characters")
async def get_characters():
    """获取角色列表"""
    try:
        characters_dir = "characters"
        
        if not os.path.isdir(characters_dir):
            os.makedirs(characters_dir, exist_ok=True)
            return {"characters": []}
        
        characters = []
        for item in os.listdir(characters_dir):
            if os.path.isdir(os.path.join(characters_dir, item)):
                characters.append(item)
        
        return {"characters": sorted(characters)}
        
    except Exception as e:
        logger.error(f"Get characters error: {e}")
        return {"characters": [], "error": str(e)}

@app.post("/test-gemini")
async def test_gemini():
    """测试Gemini API"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'your_key_here':
        return {"success": False, "error": "GEMINI_API_KEY not set"}
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Generate a simple test response")
        
        if response and response.text:
            return {
                "success": True, 
                "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
            }
        else:
            return {"success": False, "error": "No response from Gemini"}
            
    except Exception as e:
        logger.error(f"Gemini test error: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")
