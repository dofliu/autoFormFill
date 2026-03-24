#!/usr/bin/env python3
"""
簡單的 Phase 6.4 CI/CD 驗證腳本
只檢查必需文件是否存在
"""
import os
import sys
from pathlib import Path

def check_file(path, description):
    """檢查文件是否存在"""
    if Path(path).exists():
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[ERROR] {description}: {path} (文件不存在)")
        return False

def check_dir(path, description):
    """檢查目錄是否存在"""
    if Path(path).exists() and Path(path).is_dir():
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[ERROR] {description}: {path} (目錄不存在)")
        return False

def main():
    """主驗證函數"""
    print("Phase 6.4 CI/CD 文件檢查")
    print("=" * 60)
    
    # 切換到專案根目錄
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"專案目錄: {project_root}")
    
    # 必需的文件和目錄
    checks = [
        (".github/workflows/ci.yml", "CI 工作流文件"),
        (".github/workflows/deploy.yml", "CD 工作流文件"),
        (".env.example", "環境變數模板"),
        (".env.docker", "Docker 環境變數文件"),
        ("docker-compose.yml", "Docker Compose 配置"),
        ("Dockerfile", "後端 Dockerfile"),
        ("Dockerfile.frontend", "前端 Dockerfile"),
        ("docs/CI_CD_GUIDE.md", "CI/CD 指南文檔"),
        ("docs/DEPLOYMENT_GUIDE.md", "部署指南文檔"),
        ("docs/ENVIRONMENT_VARIABLES.md", "環境變數管理文檔"),
        ("docs/ENVIRONMENT_VARIABLES_PHASE_6_4.md", "Phase 6.4 環境變數指南"),
        ("docs/PHASE_6_4_COMPLETION_CHECKLIST.md", "Phase 6.4 完成檢查清單"),
        ("README_CI_CD.md", "CI/CD README"),
        ("PHASE_6_4_CI_CD_COMPLETION.md", "Phase 6.4 完成報告"),
    ]
    
    results = []
    for path, description in checks:
        result = check_file(path, description)
        results.append(result)
    
    print("\n" + "=" * 60)
    print("檢查結果總結:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"通過: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] Phase 6.4 CI/CD 所有必需文件都存在！")
        print("CI/CD 配置完整，可以進行部署。")
        return 0
    else:
        print(f"\n[WARNING] Phase 6.4 CI/CD 文件不完整 ({passed}/{total})")
        print("請創建缺失的文件。")
        return 1

if __name__ == "__main__":
    sys.exit(main())