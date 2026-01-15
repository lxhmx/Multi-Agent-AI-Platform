#!/bin/bash
# 一键更新部署脚本

cd /opt/app

echo "拉取最新代码..."
git pull

echo "停止旧服务..."
sudo docker compose down

echo "重新构建并启动..."
sudo docker compose up -d --build

echo "查看状态..."
sudo docker compose ps

echo "完成！"
