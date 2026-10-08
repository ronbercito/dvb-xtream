#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Ejecuta este script como root: sudo ./scripts/install-debian.sh" >&2
  exit 1
fi
if [[ ! -f pyproject.toml || ! -d dvb_xtream ]]; then
  echo "Ejecuta el instalador desde la raíz del repositorio clonado." >&2
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip ca-certificates openssl
getent passwd dvb-xtream >/dev/null || useradd --system --home-dir /var/lib/dvb-xtream --no-create-home --shell /usr/sbin/nologin dvb-xtream
install -d -o dvb-xtream -g dvb-xtream -m 0750 /var/lib/dvb-xtream
install -d -o root -g root -m 0755 /opt/dvb-xtream
cp -a dvb_xtream pyproject.toml /opt/dvb-xtream/
chown -R root:root /opt/dvb-xtream
python3 -m venv /opt/dvb-xtream/venv
/opt/dvb-xtream/venv/bin/pip install --upgrade pip
/opt/dvb-xtream/venv/bin/pip install /opt/dvb-xtream

if [[ ! -f /etc/dvb-xtream.env ]]; then
  admin_key="$(openssl rand -hex 32)"
  cat > /etc/dvb-xtream.env <<EOF
DVB_XTREAM_DB=/var/lib/dvb-xtream/data.sqlite3
DVB_XTREAM_ADMIN_KEY=${admin_key}
DVB_XTREAM_PUBLIC_URL=http://127.0.0.1:8000
TVH_BASE_URL=http://127.0.0.1:9981
TVH_USERNAME=
TVH_PASSWORD=
EOF
  chmod 0600 /etc/dvb-xtream.env
  echo "Se creó /etc/dvb-xtream.env con una clave de administración aleatoria. Guárdala antes de entrar al panel."
fi

cat > /etc/systemd/system/dvb-xtream.service <<'EOF'
[Unit]
Description=DVB-Xtream local IPTV service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=dvb-xtream
Group=dvb-xtream
WorkingDirectory=/opt/dvb-xtream
EnvironmentFile=/etc/dvb-xtream.env
ExecStart=/opt/dvb-xtream/venv/bin/uvicorn dvb_xtream.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/dvb-xtream

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now dvb-xtream
systemctl restart dvb-xtream
echo "Servicio: systemctl status dvb-xtream"
echo "Panel: http://IP_DEL_CONTENEDOR:8000/admin"
echo "API:   http://IP_DEL_CONTENEDOR:8000/player_api.php"
echo "Configura DVB_XTREAM_PUBLIC_URL en /etc/dvb-xtream.env con la URL/IP que usarán tus clientes."
