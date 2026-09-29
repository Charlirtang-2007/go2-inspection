#!/bin/bash
# AI机台部署脚本
set -e

# 获取脚本所在目录的绝对路径（关键修复）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. 系统依赖
sudo apt update
sudo apt install -y cmake git build-essential libssl-dev python3-venv

# 2. 编译 CycloneDDS（如果没有）
if [ ! -d "$HOME/cyclonedds/install" ]; then
    cd ~
    if [ ! -d "cyclonedds" ]; then
        git clone https://github.com/eclipse-cyclonedds/cyclonedds -b releases/0.10.x
    fi
    cd cyclonedds
    mkdir -p build install
    cd build
    cmake .. -DCMAKE_INSTALL_PREFIX=../install
    cmake --build . --target install
fi

# 3. 环境变量
export CYCLONEDDS_HOME=$HOME/cyclonedds/install
if ! grep -q "CYCLONEDDS_HOME" ~/.bashrc; then
    echo "export CYCLONEDDS_HOME=$HOME/cyclonedds/install" >> ~/.bashrc
fi

# 4. Python 环境（回到脚本目录）
cd "$SCRIPT_DIR"

# 确认 requirements.txt 存在
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 在当前目录找不到 requirements.txt"
    echo "当前目录: $(pwd)"
    exit 1
fi

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ 部署完成"
echo "项目目录: $SCRIPT_DIR"
echo "虚拟环境: $SCRIPT_DIR/venv"