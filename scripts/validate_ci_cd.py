#!/usr/bin/env python3
"""
Phase 6.4 CI/CD 配置驗證腳本
驗證所有必需的 CI/CD 文件是否存在且配置正確
"""
import os
import sys
import yaml
from pathlib import Path

def print_header(text):
    """打印標題"""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}")

def check_file_exists(path, description):
    """檢查文件是否存在"""
    if Path(path).exists():
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[ERROR] {description}: {path} (文件不存在)")
        return False

def check_yaml_syntax(path, description):
    """檢查 YAML 語法"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print(f"[OK] {description}: YAML 語法正確")
        return True
    except yaml.YAMLError as e:
        print(f"[ERROR] {description}: YAML 語法錯誤 - {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {description}: 讀取錯誤 - {e}")
        return False

def check_ci_yml():
    """檢查 CI 工作流配置"""
    print_header("檢查 CI 工作流 (ci.yml)")
    
    ci_path = ".github/workflows/ci.yml"
    if not check_file_exists(ci_path, "CI 工作流文件"):
        return False
    
    if not check_yaml_syntax(ci_path, "CI 工作流"):
        return False
    
    try:
        with open(ci_path, 'r', encoding='utf-8') as f:
            ci_config = yaml.safe_load(f)
        
        # 檢查基本結構
        required_keys = ['name', 'on', 'jobs']
        for key in required_keys:
            if key not in ci_config:
                print(f"[ERROR] CI 工作流缺少必需鍵: {key}")
                return False
        
        # 檢查觸發條件
        triggers = ci_config.get('on', {})
        if not triggers:
            print("[ERROR] CI 工作流缺少觸發條件")
            return False
        
        # 檢查環境變數
        env_vars = ci_config.get('env', {})
        required_env_vars = ['GEMINI_API_KEY', 'DATABASE_URL']
        for var in required_env_vars:
            if var not in env_vars:
                print(f"[WARN] CI 工作流缺少環境變數: {var} (可能通過 secrets 設置)")
        
        # 檢查工作
        jobs = ci_config.get('jobs', {})
        required_jobs = ['lint-and-test', 'security-scan', 'docker-build-test']
        for job in required_jobs:
            if job not in jobs:
                print(f"[ERROR] CI 工作流缺少工作: {job}")
                return False
        
        print("[OK] CI 工作流配置完整")
        return True
        
    except Exception as e:
        print(f"[ERROR] 檢查 CI 工作流時出錯: {e}")
        return False

def check_deploy_yml():
    """檢查部署工作流配置"""
    print_header("檢查 CD 工作流 (deploy.yml)")
    
    deploy_path = ".github/workflows/deploy.yml"
    if not check_file_exists(deploy_path, "CD 工作流文件"):
        return False
    
    if not check_yaml_syntax(deploy_path, "CD 工作流"):
        return False
    
    try:
        with open(deploy_path, 'r', encoding='utf-8') as f:
            deploy_config = yaml.safe_load(f)
        
        # 檢查基本結構
        required_keys = ['name', 'on', 'jobs']
        for key in required_keys:
            if key not in deploy_config:
                print(f"❌ CD 工作流缺少必需鍵: {key}")
                return False
        
        # 檢查觸發條件
        triggers = deploy_config.get('on', {})
        if not triggers:
            print("❌ CD 工作流缺少觸發條件")
            return False
        
        # 檢查環境變數
        env_vars = deploy_config.get('env', {})
        required_env_vars = ['DOCKER_BUILDKIT', 'REGISTRY']
        for var in required_env_vars:
            if var not in env_vars:
                print(f"⚠️  CD 工作流缺少環境變數: {var}")
        
        # 檢查工作
        jobs = deploy_config.get('jobs', {})
        required_jobs = ['build-and-push', 'generate-deployment-artifacts']
        for job in required_jobs:
            if job not in jobs:
                print(f"❌ CD 工作流缺少工作: {job}")
                return False
        
        print("✅ CD 工作流配置完整")
        return True
        
    except Exception as e:
        print(f"❌ 檢查 CD 工作流時出錯: {e}")
        return False

def check_deployment_files():
    """檢查部署相關文件"""
    print_header("檢查部署文件")
    
    deployment_dir = Path("deployment")
    if not deployment_dir.exists():
        print("❌ deployment 目錄不存在")
        return False
    
    required_files = [
        ('deploy.sh', '主部署腳本'),
        ('update.sh', '更新腳本'),
        ('rollback.sh', '回滾腳本'),
        ('monitor.sh', '監控腳本'),
        ('backup.sh', '備份腳本'),
        ('restore.sh', '恢復腳本'),
    ]
    
    all_exist = True
    for filename, description in required_files:
        file_path = deployment_dir / filename
        if not file_path.exists():
            print(f"❌ {description}: {file_path} (文件不存在)")
            all_exist = False
        else:
            # 檢查文件是否可執行
            if os.access(file_path, os.X_OK):
                print(f"✅ {description}: {file_path} (可執行)")
            else:
                print(f"⚠️  {description}: {file_path} (不可執行，請運行 chmod +x)")
    
    return all_exist

def check_env_files():
    """檢查環境變數文件"""
    print_header("檢查環境變數文件")
    
    required_files = [
        ('.env.example', '環境變數模板'),
        ('.env.docker', 'Docker 環境變數'),
    ]
    
    all_exist = True
    for filename, description in required_files:
        if not Path(filename).exists():
            print(f"❌ {description}: {filename} (文件不存在)")
            all_exist = False
        else:
            print(f"✅ {description}: {filename}")
    
    return all_exist

def check_docker_files():
    """檢查 Docker 文件"""
    print_header("檢查 Docker 文件")
    
    required_files = [
        ('docker-compose.yml', 'Docker Compose 配置'),
        ('Dockerfile', '後端 Dockerfile'),
        ('Dockerfile.frontend', '前端 Dockerfile'),
    ]
    
    all_exist = True
    for filename, description in required_files:
        if not Path(filename).exists():
            print(f"❌ {description}: {filename} (文件不存在)")
            all_exist = False
        else:
            print(f"✅ {description}: {filename}")
    
    return all_exist

def check_documentation():
    """檢查文檔文件"""
    print_header("檢查文檔文件")
    
    docs_dir = Path("docs")
    if not docs_dir.exists():
        print("❌ docs 目錄不存在")
        return False
    
    required_files = [
        ('CI_CD_GUIDE.md', 'CI/CD 指南'),
        ('DEPLOYMENT_GUIDE.md', '部署指南'),
        ('ENVIRONMENT_VARIABLES.md', '環境變數管理'),
        ('ENVIRONMENT_VARIABLES_PHASE_6_4.md', 'Phase 6.4 環境變數指南'),
        ('PHASE_6_4_COMPLETION_CHECKLIST.md', 'Phase 6.4 完成檢查清單'),
    ]
    
    all_exist = True
    for filename, description in required_files:
        file_path = docs_dir / filename
        if not file_path.exists():
            print(f"❌ {description}: {file_path} (文件不存在)")
            all_exist = False
        else:
            print(f"✅ {description}: {file_path}")
    
    return all_exist

def main():
    """主驗證函數"""
    print("Phase 6.4 CI/CD 配置驗證")
    print("="*60)
    
    # 切換到專案根目錄
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"專案目錄: {project_root}")
    
    # 執行所有檢查
    checks = [
        ("CI 工作流", check_ci_yml),
        ("CD 工作流", check_deploy_yml),
        ("部署文件", check_deployment_files),
        ("環境變數文件", check_env_files),
        ("Docker 文件", check_docker_files),
        ("文檔文件", check_documentation),
    ]
    
    results = []
    for name, check_func in checks:
        print_header(f"開始檢查: {name}")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ 檢查 {name} 時出錯: {e}")
            results.append((name, False))
    
    # 總結結果
    print_header("驗證結果總結")
    
    passed = 0
    total = len(results)
    
    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{name}: {status}")
        if result:
            passed += 1
    
    print(f"\n總計: {passed}/{total} 項檢查通過")
    
    if passed == total:
        print("\nPhase 6.4 CI/CD 配置驗證完全通過！")
        print("所有必需的 CI/CD 文件都存在且配置正確。")
        return 0
    else:
        print(f"\nPhase 6.4 CI/CD 配置驗證部分通過 ({passed}/{total})")
        print("請修復上述問題以完成 Phase 6.4。")
        return 1

if __name__ == "__main__":
    sys.exit(main())