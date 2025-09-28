#!/bin/bash
set -e

echo "🔧 Updating system..."
sudo apt update && sudo apt -y upgrade

echo "🔧 Installing dependencies..."
sudo apt install -y git redis-server tmux python3 python3-pip python3-venv setserial

echo "🔧 Cloning pyEfi..."
cd /home/pi
if [ ! -d pyEfi ]; then
  git clone https://github.com/lucid281/pyEfi.git
fi
cd pyEfi

echo "🔧 Setting up Python virtual environment..."
python3 -m venv pyefi-venv
source pyefi-venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "🔧 Configuring Redis to use Unix socket..."
sudo sed -i 's/^# *unixsocket .*/unixsocket \/var\/run\/redis\/redis.sock/' /etc/redis/redis.conf
sudo sed -i 's/^# *unixsocketperm .*/unixsocketperm 770/' /etc/redis/redis.conf
sudo systemctl enable redis
sudo systemctl restart redis
sudo usermod -aG redis pi

echo "🔧 Adding pi user to dialout group (serial access)..."
sudo usermod -aG dialout pi

echo "🔧 Creating systemd service for pyEfi..."
sudo tee /etc/systemd/system/pyefi.service > /dev/null <<'EOF'
[Unit]
Description=pyEfi Collector
After=network.target redis.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pyEfi
ExecStart=/home/pi/pyEfi/pyefi-venv/bin/python ./pyefi.py run collectMS microsquirt.ini /dev/ttyUSB0 test
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "🔧 Enabling and starting pyEfi service..."
sudo systemctl daemon-reload
sudo systemctl enable pyefi
sudo systemctl start pyefi

echo "✅ Setup complete!"
echo "➡️ Reboot your Pi for all group changes to take effect: sudo reboot"
