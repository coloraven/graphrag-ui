# syntax=docker/dockerfile:1

# 中国大陆网络加速：构建时可覆盖以下 ARG（见 docker-compose.yml）
ARG PYTHON_IMAGE=docker.linkos.org/library/python:3.11-slim-bookworm
ARG DEBIAN_MIRROR=mirrors.aliyun.com
ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com
ARG UV_VERSION=0.6.14

FROM ${PYTHON_IMAGE} AS base

ARG DEBIAN_MIRROR=mirrors.aliyun.com
ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com
ARG UV_VERSION=0.6.14

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_INDEX_URL=${PYPI_INDEX_URL} \
    PIP_INDEX_URL=${PYPI_INDEX_URL} \
    PIP_TRUSTED_HOST=${PYPI_TRUSTED_HOST} \
    PATH="/app/.venv/bin:$PATH"

# Debian Bookworm apt 换源（阿里云镜像）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|http://deb.debian.org|https://${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|http://security.debian.org|https://${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i "s|deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list; \
        sed -i "s|security.debian.org|${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 通过 PyPI 镜像安装 uv，避免拉取 ghcr.io
RUN pip install --no-cache-dir \
    --index-url "${PYPI_INDEX_URL}" \
    --trusted-host "${PYPI_TRUSTED_HOST}" \
    "uv==${UV_VERSION}"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# 依赖安装走国内 PyPI 镜像
RUN uv sync --frozen --no-dev --index-url "${PYPI_INDEX_URL}"

COPY frontend ./frontend
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8012

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8012/api/health', timeout=5)"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["serve"]
