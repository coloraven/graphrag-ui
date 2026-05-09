from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import uvicorn

from .app import create_app
from .evaluation import run_evaluation
from .indexing import IndexBuildError, get_index_status, rebuild_index
from .settings import load_settings

# 暂时注释缺失的模块导入
# from .benchmark import run_benchmark
# from .graphrag_fallback import apply_graphrag_fallback_patch
# apply_graphrag_fallback_patch()



def main() -> None:
    parser = argparse.ArgumentParser(prog="reggraph-assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("serve")
    subparsers.add_parser("index")
    subparsers.add_parser("status")
    subparsers.add_parser("eval")

    # 添加benchmark命令
    benchmark_parser = subparsers.add_parser("benchmark", help="Run performance benchmark")
    benchmark_parser.add_argument(
        "--output",
        type=Path,
        default=Path("workspace/benchmark_results.json"),
        help="Output file path for results",
    )

    args = parser.parse_args()

    settings = load_settings()
    if args.command == "serve":
        uvicorn.run(create_app(settings), host="127.0.0.1", port=settings.port)
        return
    if args.command == "index":
        try:
            result = rebuild_index(settings)
            sys.stdout.write(json.dumps(result.model_dump(), ensure_ascii=False) + "\n")
        except IndexBuildError as e:
            sys.stderr.write(f"索引构建失败: {e}\n")
            sys.exit(1)
        return
    if args.command == "eval":
        sys.stdout.write(json.dumps(run_evaluation(settings).model_dump(), ensure_ascii=False) + "\n")
        return
    if args.command == "benchmark":
        sys.stderr.write("benchmark 命令暂未实现\n")
        sys.exit(1)
        return
    sys.stdout.write(json.dumps(get_index_status(settings.paths).model_dump(), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
