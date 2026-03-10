# ---- 构建阶段 ----
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安装构建工具（nonebot-plugin-rikka-extra 含 Cython 扩展，需要 gcc）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境并使用 pip 安装运行时依赖
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 先复制构建项目所需最小文件，充分利用 Docker 层缓存
COPY pyproject.toml ./
COPY README.md ./
COPY nonebot_plugin_rikka/ ./nonebot_plugin_rikka/

# 安装项目及驱动运行所需 extra
RUN pip install --upgrade pip setuptools wheel && \
    pip install . && \
    pip install "nonebot2[fastapi,httpx,websockets]>=2.3.0"


# ---- 运行阶段 ----
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安装 Playwright 运行时所需系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libatspi2.0-0 libwayland-client0 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制已安装的虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 将项目 venv 加入 PATH
ENV PATH="/app/.venv/bin:$PATH"

# 安装 pipx 并通过 pipx 安装 nb-cli（入口脚本方式）
RUN pip install pipx && pipx install nb-cli
ENV PATH="/root/.local/bin:$PATH"

# 安装 Playwright Chromium 及其系统依赖
RUN playwright install --with-deps chromium

# 复制应用代码（不含 bot.py，使用 nb run 启动）
COPY pyproject.toml ./
COPY README.md ./
COPY nonebot_plugin_rikka/ ./nonebot_plugin_rikka/
COPY docker-entrypoint.sh ./docker-entrypoint.sh

# 通过 nb-cli 安装 QQ 适配器
RUN nb adapter install nonebot-adapter-qq

# 创建运行时所需目录
RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/static /app/logs /app/data

EXPOSE 8080

CMD ["sh", "docker-entrypoint.sh"]
