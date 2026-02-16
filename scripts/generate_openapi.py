#!/usr/bin/env python3
"""生成当前 API 的 OpenAPI 规范文件"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_openapi():
    """生成 OpenAPI JSON 文件"""
    try:
        # 导入主应用
        from src.api.main_api_server import create_app

        print("正在创建 FastAPI 应用...")
        app = create_app()

        print("正在生成 OpenAPI schema...")
        # 获取 OpenAPI schema
        openapi_schema = app.openapi()

        # 保存到文件
        output_path = Path("docs/api/openapi.current.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

        # 统计信息
        total_endpoints = len([r for r in app.routes if hasattr(r, "methods")])
        tags = set()
        if "tags" in openapi_schema:
            tags = {tag["name"] for tag in openapi_schema["tags"]}
        elif "paths" in openapi_schema:
            # 从路径中提取 tags
            for path_data in openapi_schema["paths"].values():
                for method_data in path_data.values():
                    if isinstance(method_data, dict) and "tags" in method_data:
                        tags.update(method_data["tags"])

        print(f"\n✅ OpenAPI schema generated: {output_path}")
        print(f"   Total endpoints: {total_endpoints}")
        print(f"   API Title: {openapi_schema.get('info', {}).get('title', 'N/A')}")
        print(f"   API Version: {openapi_schema.get('info', {}).get('version', 'N/A')}")
        print(f"   Tags: {sorted(tags)}")

        return 0

    except Exception as e:
        print(f"\n❌ Error generating OpenAPI schema: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(generate_openapi())
