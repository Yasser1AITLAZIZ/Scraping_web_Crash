FROM python:3.10-slim

# --------------------------
# Install dependencies for Chrome and Xvfb
# --------------------------
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    ca-certificates \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnss3 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libgtk-3-0 \
    libu2f-udev \
    xdg-utils \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome’s official GPG key and stable repo
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# --------------------------
# Setup working directory
# --------------------------
WORKDIR /app

# --------------------------
# Copy Python requirements and install them
# --------------------------
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------
# Copy your project code
# --------------------------
COPY . /app

# --------------------------
# Environment variables
# --------------------------
ENV DISPLAY=:99
ENV PYTHONPATH=/app/

# --------------------------
# Start Xvfb before running Chrome
# --------------------------
# Lancement de Xvfb en arrière-plan
RUN Xvfb :99 -screen 0 1920x1080x24 &

# Note : Pour s'assurer que Xvfb tourne bien au lancement du conteneur, 
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]


# --------------------------
# Commande de lancement
# --------------------------
CMD ["streamlit", "run", "app.py"]
