#!/usr/bin/env python3
"""
AI Agent Optimized Story Generation Server
==========================================

专门为AI agent访问优化的Web服务器，提供简洁的API和界面
确保Playwright能够稳定自动化访问和生成故事。

Features:
- AI agent友好的DOM结构
- 稳定的选择器ID
- 实时状态反馈
- 错误恢复机制
"""

import asyncio
import logging
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import LLM service
try:
    from src.llm_service import LLMRequest, ResponseFormat, get_llm_service

    LLM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LLM service not available: {e}")
    LLM_AVAILABLE = False

app = Flask(__name__)
app.config["SECRET_KEY"] = "ai_agent_story_server_key"
app.config["JSON_AS_ASCII"] = False

# Disable Flask logging for cleaner output
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# AI Agent Optimized HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Novel Engine - AI Agent Story Generator</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.2em;
        }
        .subtitle {
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .status-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #27ae60;
            color: white;
            padding: 12px 20px;
            border-radius: 25px;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1000;
        }
        .input-section {
            margin-bottom: 30px;
        }
        label {
            display: block;
            margin-bottom: 10px;
            font-weight: bold;
            color: #2c3e50;
        }
        #story-prompt {
            width: 100%;
            height: 120px;
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 15px;
            font-size: 16px;
            font-family: inherit;
            resize: vertical;
            box-sizing: border-box;
        }
        #story-prompt:focus {
            outline: none;
            border-color: #2980b9;
            box-shadow: 0 0 10px rgba(52, 152, 219, 0.3);
        }
        #generate-button {
            background: linear-gradient(45deg, #3498db, #2980b9);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 18px;
            font-weight: bold;
            transition: all 0.3s ease;
            display: block;
            margin: 20px auto;
        }
        #generate-button:hover:not(:disabled) {
            background: linear-gradient(45deg, #2980b9, #34495e);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        #generate-button:disabled {
            background: #95a5a6;
            cursor: not-allowed;
            transform: none;
        }
        .output-section {
            margin-top: 40px;
            padding: 30px;
            background: #ecf0f1;
            border-radius: 10px;
            border-left: 5px solid #3498db;
            display: none;
        }
        #story-output {
            font-size: 16px;
            line-height: 1.8;
            color: #2c3e50;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .loading {
            text-align: center;
            color: #3498db;
            font-style: italic;
            font-size: 18px;
        }
        .error {
            color: #e74c3c;
            font-weight: bold;
            background: #fdf2f2;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #e74c3c;
        }
        .success {
            color: #27ae60;
        }
        .meta-info {
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #bdc3c7;
        }
        .preset-prompts {
            margin-bottom: 20px;
        }
        .preset-button {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s ease;
        }
        .preset-button:hover {
            background: #e9ecef;
            border-color: #3498db;
        }
    </style>
</head>
<body>
    <div class="status-indicator" id="status-indicator">🤖 AI Ready</div>
    
    <div class="container">
        <h1>🎭 Novel Engine</h1>
        <p class="subtitle">AI Agent Story Generation Interface</p>
        
        <div class="input-section">
            <label for="story-prompt">Story Generation Prompt:</label>
            
            <div class="preset-prompts">
                <strong>Quick Presets:</strong><br>
                <button type="button" class="preset-button" onclick="setPresetPrompt('time_paradox')">Time Paradox</button>
                <button type="button" class="preset-button" onclick="setPresetPrompt('meta_narrative')">Meta-Narrative</button>
                <button type="button" class="preset-button" onclick="setPresetPrompt('quantum_consciousness')">Quantum Consciousness</button>
                <button type="button" class="preset-button" onclick="setPresetPrompt('mystery')">Mystery</button>
                <button type="button" class="preset-button" onclick="setPresetPrompt('adventure')">Adventure</button>
            </div>
            
            <textarea 
                id="story-prompt" 
                name="prompt" 
                placeholder="Enter your creative story prompt here... The AI will generate an original story based on your input."
                data-testid="story-prompt-input"
                required
            ></textarea>
            
            <button 
                type="button" 
                id="generate-button" 
                onclick="generateStory()"
                data-testid="generate-story-button"
            >
                🚀 Generate Story with AI
            </button>
        </div>
        
        <div id="output-section" class="output-section" data-testid="story-output-section">
            <div id="story-output" data-testid="story-output-content"></div>
            <div id="meta-info" class="meta-info"></div>
        </div>
    </div>

    <script>
        // Preset prompts for easy testing
        const presetPrompts = {
            time_paradox: "Write a story where the main character travels back in time to prevent a disaster, but realizes their actions might create a worse timeline. Include specific dialogue and internal conflict.",
            meta_narrative: "Create a story where the protagonist gradually realizes they are a character in a story being written. Show their attempts to communicate with the author and break free from the narrative.",
            quantum_consciousness: "Write about a character who exists in multiple parallel realities simultaneously. They can perceive all versions of themselves but struggle to make decisions when every choice leads to different outcomes.",
            mystery: "Create a detective story where the investigator discovers that they themselves are the criminal, but have no memory of committing the crime. Include psychological elements.",
            adventure: "Write an adventure story where the hero must choose between saving their hometown or pursuing their lifelong dream. Make both choices equally compelling."
        };
        
        function setPresetPrompt(type) {
            const textarea = document.getElementById('story-prompt');
            textarea.value = presetPrompts[type];
            textarea.focus();
        }
        
        async function generateStory() {
            const promptInput = document.getElementById('story-prompt');
            const generateButton = document.getElementById('generate-button');
            const outputSection = document.getElementById('output-section');
            const storyOutput = document.getElementById('story-output');
            const metaInfo = document.getElementById('meta-info');
            const statusIndicator = document.getElementById('status-indicator');
            
            const prompt = promptInput.value.trim();
            
            if (!prompt) {
                alert('Please enter a story prompt first.');
                promptInput.focus();
                return;
            }
            
            // Update UI for generation state
            generateButton.disabled = true;
            generateButton.textContent = '⏳ AI is Generating Story...';
            outputSection.style.display = 'block';
            storyOutput.innerHTML = '<div class="loading">🤖 AI is thinking and creating your story... This may take 10-30 seconds for complex prompts.</div>';
            metaInfo.innerHTML = '';
            statusIndicator.textContent = '🔄 Generating...';
            statusIndicator.style.background = '#f39c12';
            
            const startTime = Date.now();
            
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ prompt: prompt })
                });
                
                const result = await response.json();
                const endTime = Date.now();
                const responseTime = endTime - startTime;
                
                if (result.success) {
                    storyOutput.innerHTML = `
                        <div class="success">
                            <h3>✅ AI Generated Story</h3>
                            <div style="margin-top: 20px;">${result.content}</div>
                        </div>
                    `;
                    
                    metaInfo.innerHTML = `
                        <strong>Generation Statistics:</strong><br>
                        • Response Time: ${responseTime}ms<br>
                        • Content Length: ${result.content.length} characters<br>
                        • Words: ~${result.content.split(' ').length}<br>
                        • AI Provider: ${result.provider || 'Unknown'}<br>
                        • Cached: ${result.cached ? 'Yes' : 'No'}<br>
                        • Generated: ${new Date().toLocaleTimeString()}<br>
                        • Tokens Used: ${result.tokens_used || 'N/A'}<br>
                        • Cost Estimate: $${result.cost_estimate || 'N/A'}
                    `;
                    
                    statusIndicator.textContent = '✅ Story Generated';
                    statusIndicator.style.background = '#27ae60';
                } else {
                    storyOutput.innerHTML = `
                        <div class="error">
                            <h3>❌ Story Generation Failed</h3>
                            <p>${result.error || 'Unknown error occurred'}</p>
                            <p><strong>Error Type:</strong> ${result.error_type || 'Unknown'}</p>
                        </div>
                    `;
                    
                    metaInfo.innerHTML = `
                        <strong>Error Information:</strong><br>
                        • Response Time: ${responseTime}ms<br>
                        • Error Type: ${result.error_type || 'Unknown'}<br>
                        • Provider: ${result.provider || 'Unknown'}<br>
                        • Time: ${new Date().toLocaleTimeString()}
                    `;
                    
                    statusIndicator.textContent = '❌ Generation Failed';
                    statusIndicator.style.background = '#e74c3c';
                }
                
            } catch (error) {
                const endTime = Date.now();
                const responseTime = endTime - startTime;
                
                storyOutput.innerHTML = `
                    <div class="error">
                        <h3>❌ Request Failed</h3>
                        <p>Network or server error: ${error.message}</p>
                    </div>
                `;
                
                metaInfo.innerHTML = `
                    <strong>Request Information:</strong><br>
                    • Response Time: ${responseTime}ms<br>
                    • Error: ${error.message}<br>
                    • Time: ${new Date().toLocaleTimeString()}
                `;
                
                statusIndicator.textContent = '🚫 Request Failed';
                statusIndicator.style.background = '#e74c3c';
            }
            
            // Reset button
            generateButton.disabled = false;
            generateButton.textContent = '🚀 Generate Story with AI';
            
            // Reset status after delay
            setTimeout(() => {
                statusIndicator.textContent = '🤖 AI Ready';
                statusIndicator.style.background = '#27ae60';
            }, 3000);
        }
        
        // Add keyboard shortcut
        document.getElementById('story-prompt').addEventListener('keydown', function(event) {
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                event.preventDefault();
                generateStory();
            }
        });
        
        // Auto-focus on load
        window.addEventListener('load', function() {
            document.getElementById('story-prompt').focus();
        });
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Main story generation interface optimized for AI agents."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/generate", methods=["POST"])
def generate_story():
    """
    Generate story using real AI - optimized for AI agent testing.

    Returns consistent JSON structure for reliable parsing.
    """
    try:
        data = request.get_json()
        if not data or "prompt" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No prompt provided in request body",
                        "error_type": "missing_prompt",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                400,
            )

        prompt = data["prompt"].strip()
        if not prompt:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Empty prompt provided",
                        "error_type": "empty_prompt",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                400,
            )

        if not LLM_AVAILABLE:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "LLM service not available - check API keys configuration",
                        "error_type": "service_unavailable",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                503,
            )

        # Log the generation request
        print(f"🎯 AI Story Generation Request: {prompt[:100]}...")

        # Get LLM service and generate response
        llm_service = get_llm_service()

        # Create request with optimized settings for story generation
        llm_request = LLMRequest(
            prompt=f"Create an original, creative story based on this prompt: {prompt}",
            response_format=ResponseFormat.NARRATIVE_FORMAT,
            temperature=0.8,  # High creativity
            max_tokens=2500,  # Allow longer stories
            requester="ai_agent_story_server",
        )

        # Generate response - use asyncio.run for sync context
        start_time = time.time()
        response = asyncio.run(llm_service.generate(llm_request))
        generation_time = int((time.time() - start_time) * 1000)

        if response.content and not response.content.startswith("[LLM Error"):
            print(
                f"✅ Story generated successfully: {len(response.content)} chars in {generation_time}ms"
            )

            return jsonify(
                {
                    "success": True,
                    "content": response.content,
                    "provider": response.provider.value,
                    "cached": response.cached,
                    "response_time_ms": generation_time,
                    "tokens_used": response.tokens_used,
                    "cost_estimate": response.cost_estimate,
                    "timestamp": datetime.now().isoformat(),
                    "word_count": len(response.content.split()),
                    "char_count": len(response.content),
                }
            )
        else:
            print(f"❌ Story generation failed: {response.content}")

            return (
                jsonify(
                    {
                        "success": False,
                        "error": response.content or "AI generation failed",
                        "error_type": "generation_failed",
                        "provider": response.provider.value if response else "unknown",
                        "response_time_ms": generation_time,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"❌ Server error in /api/generate: {e}")
        print(f"Traceback: {error_traceback}")

        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Server error: {str(e)}",
                    "error_type": "server_error",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@app.route("/api/health")
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify(
        {
            "status": "healthy",
            "service": "ai_agent_story_server",
            "llm_available": LLM_AVAILABLE,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
        }
    )


@app.route("/api/test-prompts")
def get_test_prompts():
    """Get predefined test prompts for AI agent testing."""
    return jsonify(
        {
            "prompts": [
                {
                    "id": "time_paradox",
                    "name": "Time Paradox Challenge",
                    "prompt": "Write a story where the main character travels back in time to prevent a disaster, but realizes their actions might create a worse timeline. Include specific dialogue and internal conflict.",
                    "complexity": 5,
                    "expected_elements": [
                        "time travel",
                        "paradox",
                        "dialogue",
                        "internal conflict",
                    ],
                },
                {
                    "id": "meta_narrative",
                    "name": "Meta-Narrative Awareness",
                    "prompt": "Create a story where the protagonist gradually realizes they are a character in a story being written. Show their attempts to communicate with the author and break free from the narrative.",
                    "complexity": 4,
                    "expected_elements": [
                        "meta-fiction",
                        "self-awareness",
                        "fourth wall",
                        "author interaction",
                    ],
                },
                {
                    "id": "quantum_consciousness",
                    "name": "Quantum Consciousness Split",
                    "prompt": "Write about a character who exists in multiple parallel realities simultaneously. They can perceive all versions of themselves but struggle to make decisions when every choice leads to different outcomes.",
                    "complexity": 5,
                    "expected_elements": [
                        "quantum",
                        "parallel realities",
                        "consciousness",
                        "decision making",
                    ],
                },
            ]
        }
    )


def run_server(host="0.0.0.0", port=8080, debug=False):
    """Run the AI agent optimized story server."""
    print("🎭 Starting AI Agent Story Generation Server...")
    print(f"📍 Server URL: http://{host}:{port}")
    print("🤖 Optimized for AI agent access with Playwright")
    print("=" * 60)

    if not LLM_AVAILABLE:
        print("⚠️ WARNING: LLM service not available")
        print("   Make sure API keys are properly configured")
        print("   Server will run but story generation will fail")
    else:
        print("✅ LLM service available and ready for AI generation")

    print("\n🎯 AI Agent Testing Features:")
    print("   • Stable DOM selectors with data-testid attributes")
    print("   • Consistent JSON API responses")
    print("   • Real-time status indicators")
    print("   • Error recovery mechanisms")
    print("   • Preset prompts for automated testing")

    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    run_server(port=8080)
