#!/bin/bash
# AI机台部署脚本
set -e

# 1. 系统依赖
sudo apt update
sudo apt install -y cmake git build-essential libssl-dev python3-venv

# 2. 编译 CycloneDDS（如果没有）
if [ ! -d "$HOME/cyclonedds/install" ]; then
    cd ~
    git clone https://github.com/eclipse-cyclonedds/cyclonedds -b releases/0.10.x
    cd cyclonedds
    mkdir -p build install
    cd build
    cmake .. -DCMAKE_INSTALL_PREFIX=../install
    cmake --build . --target install
fi

# 3. 环境变量
export CYCLONEDDS_HOME=$HOME/cyclonedds/install
echo "export CYCLONEDDS_HOME=$HOME/cyclonedds/install" >> ~/.bashrc

# 4. Python 环境
cd "$(dirname "$0")"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "✅ 部署完成"