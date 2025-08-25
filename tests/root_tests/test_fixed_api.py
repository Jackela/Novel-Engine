#!/usr/bin/env python3
"""
测试修复后的API服务器
"""

import os
import sys
import time
import json
import requests
import subprocess
from datetime import datetime

def create_minimal_api_server():
    """创建最小化的API服务器用于测试"""
    
    api_code = '''#!/usr/bin/env python3
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
'''
    
    with open('minimal_api_server.py', 'w', encoding='utf-8') as f:
        f.write(api_code)
    
    print("创建了最小化API服务器: minimal_api_server.py")

def test_minimal_api():
    """测试最小化API服务器"""
    print("=== 测试最小化API服务器 ===")
    
    # 设置真实的API密钥（如果需要）
    if not os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY') == 'your_key_here':
        print("警告: GEMINI_API_KEY未设置或为占位符，将使用模拟模式")
    
    # 启动服务器
    server = subprocess.Popen([
        sys.executable, "minimal_api_server.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # 等待启动
        print("等待服务器启动...")
        time.sleep(6)
        
        base_url = "http://127.0.0.1:8003"
        results = {}
        
        print(f"测试API端点 ({base_url})...")
        
        # 1. 测试根路径
        try:
            r = requests.get(f"{base_url}/", timeout=5)
            if r.status_code == 200:
                data = r.json()
                print(f"OK / - {data.get('message', 'OK')}")
                results['root'] = {'success': True, 'data': data}
            else:
                print(f"FAIL / - Status {r.status_code}")
                results['root'] = {'success': False, 'status': r.status_code}
        except Exception as e:
            print(f"ERROR / - {e}")
            results['root'] = {'success': False, 'error': str(e)}
        
        # 2. 测试健康检查
        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            if r.status_code == 200:
                data = r.json()
                status = data.get('status', 'unknown')
                gemini_key_set = data.get('gemini_key_set', False)
                gemini_available = data.get('gemini_available', False)
                print(f"OK /health - Status: {status}, Gemini Key: {gemini_key_set}, Gemini Available: {gemini_available}")
                results['health'] = {'success': True, 'data': data}
            else:
                print(f"FAIL /health - Status {r.status_code}")
                results['health'] = {'success': False, 'status': r.status_code}
        except Exception as e:
            print(f"ERROR /health - {e}")
            results['health'] = {'success': False, 'error': str(e)}
        
        # 3. 测试字符列表
        try:
            r = requests.get(f"{base_url}/characters", timeout=5)
            if r.status_code == 200:
                data = r.json()
                chars = data.get('characters', [])
                print(f"OK /characters - Found {len(chars)} characters: {chars}")
                results['characters'] = {'success': True, 'data': data}
            else:
                print(f"FAIL /characters - Status {r.status_code}")
                results['characters'] = {'success': False, 'status': r.status_code}
        except Exception as e:
            print(f"ERROR /characters - {e}")
            results['characters'] = {'success': False, 'error': str(e)}
        
        # 4. 测试Gemini API
        try:
            r = requests.post(f"{base_url}/test-gemini", timeout=10)
            if r.status_code == 200:
                data = r.json()
                success = data.get('success', False)
                if success:
                    response_text = data.get('response', '')
                    print(f"OK /test-gemini - Response: {response_text[:50]}...")
                else:
                    error = data.get('error', 'unknown')
                    print(f"FAIL /test-gemini - Error: {error}")
                results['gemini'] = {'success': success, 'data': data}
            else:
                print(f"FAIL /test-gemini - Status {r.status_code}")
                results['gemini'] = {'success': False, 'status': r.status_code}
        except Exception as e:
            print(f"ERROR /test-gemini - {e}")
            results['gemini'] = {'success': False, 'error': str(e)}
        
        return results
        
    finally:
        # 清理服务器
        server.terminate()
        server.wait()
        print("服务器已停止")

def generate_report(results):
    """生成测试报告"""
    print("\\n=== 测试报告 ===")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r.get('success', False))
    
    print(f"总测试数: {total_tests}")
    print(f"成功测试: {successful_tests}")
    print(f"失败测试: {total_tests - successful_tests}")
    print(f"成功率: {(successful_tests/total_tests)*100:.1f}%")
    
    # 保存详细报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total_tests,
            "successful": successful_tests,
            "failed": total_tests - successful_tests,
            "success_rate": f"{(successful_tests/total_tests)*100:.1f}%"
        },
        "details": results
    }
    
    report_file = f"minimal_api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"详细报告已保存: {report_file}")
    
    return successful_tests >= total_tests * 0.75  # 75%成功率算通过

def main():
    """主函数"""
    create_minimal_api_server()
    results = test_minimal_api()
    success = generate_report(results)
    
    if success:
        print("\\nAPI功能测试通过！")
    else:
        print("\\nAPI功能测试未完全通过")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)