FROM python:3.11-slim

# Set timezone to Shanghai
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' > /etc/timezone

ENV DEBIAN_FRONTEND=noninteractive
ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1

# 安装必要工具、替换源、安装包
RUN which apt \
    && { \
         echo "deb http://mirrors.ustc.edu.cn/debian trixie main contrib non-free non-free-firmware"; \
         echo "deb http://mirrors.ustc.edu.cn/debian trixie-updates main contrib non-free non-free-firmware"; \
         echo "deb http://mirrors.ustc.edu.cn/debian-security trixie-security main contrib non-free non-free-firmware"; \
       } > /etc/apt/sources.list \
    \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates apt-transport-https gnupg dirmngr \
    && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (better layer caching)
COPY pyproject.toml .
RUN pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -e .

# Copy application code
COPY . .

# Expose port (configured in config/lessweb.toml)
EXPOSE 8080

# Start the application with migration
CMD ["sh", "-c", "make pyway-migrate && python main.py"]
