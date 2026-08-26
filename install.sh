#!/usr/bin/env bash
# install.sh - 一键安装 mua 全局命令
#
# 将 bin/mua 软链到 ~/.local/bin/mua, 之后在任意目录直接使用:
#   mua setup / mua run / mua status ...
#
# 用法:
#   ./install.sh          # 安装 (默认 ~/.local/bin)
#   INSTALL_DIR=/usr/local/bin ./install.sh   # 指定安装目录
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
TARGET="$INSTALL_DIR/mua"

# 创建安装目录
mkdir -p "$INSTALL_DIR"
chmod +x "$SCRIPT_DIR/bin/mua"

# 软链 (覆盖旧链接)
ln -sf "$SCRIPT_DIR/bin/mua" "$TARGET"
echo "[成功] 已安装: $TARGET -> $SCRIPT_DIR/bin/mua"

# 检查 PATH
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo ""
    echo "[提示] $INSTALL_DIR 不在 PATH 中, 请执行以下命令后重开终端:"
    if [[ "$INSTALL_DIR" == "$HOME/.local/bin" ]]; then
      echo "   echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
    else
      echo "   export PATH=\"$INSTALL_DIR:\$PATH\""
    fi
    ;;
esac

echo ""
echo "安装完成! 试试:"
echo "   mua whoami    # 查看凭证状态"
echo "   mua setup     # 配置 AK/SK (首次使用)"
echo "   mua run       # 问答式向导运行任务"
