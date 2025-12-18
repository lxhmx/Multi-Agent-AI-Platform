#!/bin/bash

# Text2SQL 自动部署脚本
# 用法: sudo ./deploy.sh [backend|frontend|all]

set -e

PROJECT_DIR="/opt/app/text2sql"
FRONTEND_DIR="$PROJECT_DIR/font-vue"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 拉取最新代码
pull_code() {
    log_info "拉取最新代码..."
    cd $PROJECT_DIR
    git pull origin main || git pull origin master
    log_info "代码更新完成"
}

# 更新后端
deploy_backend() {
    log_info "开始更新后端..."
    
    cd $PROJECT_DIR
    
    # 安装新依赖（如果有）
    log_info "检查 Python 依赖..."
    ./venv/bin/pip install -r requirements.txt --quiet
    
    # 重启后端服务
    log_info "重启后端服务..."
    systemctl restart text2sql
    
    # 等待服务启动
    sleep 2
    
    # 检查服务状态
    if systemctl is-active --quiet text2sql; then
        log_info "后端服务启动成功 ✓"
    else
        log_error "后端服务启动失败！"
        journalctl -u text2sql -n 20 --no-pager
        exit 1
    fi
}

# 更新前端
deploy_frontend() {
    log_info "开始更新前端..."
    
    cd $FRONTEND_DIR
    
    # 安装依赖
    log_info "安装前端依赖..."
    npm install --silent
    
    # 构建
    log_info "构建前端..."
    npm run build
    
    # 重启 Nginx
    log_info "重启 Nginx..."
    systemctl restart nginx
    
    if systemctl is-active --quiet nginx; then
        log_info "前端部署成功 ✓"
    else
        log_error "Nginx 启动失败！"
        exit 1
    fi
}

# 主逻辑
main() {
    local mode=${1:-all}
    
    echo "========================================"
    echo "  Text2SQL 自动部署脚本"
    echo "========================================"
    
    # 拉取代码
    pull_code
    
    case $mode in
        backend)
            deploy_backend
            ;;
        frontend)
            deploy_frontend
            ;;
        all)
            deploy_backend
            deploy_frontend
            ;;
        *)
            log_error "未知参数: $mode"
            echo "用法: $0 [backend|frontend|all]"
            exit 1
            ;;
    esac
    
    echo ""
    log_info "========== 部署完成 =========="
    echo ""
}

main "$@"
