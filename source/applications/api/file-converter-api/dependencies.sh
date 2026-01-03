apt-get update && \
apt-get install -y --no-install-recommends libreoffice libpango-1.0-0 libpangocairo-1.0-0 && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*
