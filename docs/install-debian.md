# Instalación de desarrollo en Debian 13

El instalador se ejecuta desde la raíz de un clon de este repositorio dentro del contenedor de desarrollo. Instala el servicio DVB-Xtream en `systemd` y lo deja escuchando en el puerto TCP 8000. Se puede volver a ejecutar para actualizar el código; conserva `/etc/dvb-xtream.env` y la base de datos.

```sh
apt-get update
apt-get install -y git
git clone https://github.com/ronbercito/dvb-xtream.git /opt/dvb-xtream-src
cd /opt/dvb-xtream-src
git switch feat/mvp-backend
bash ./scripts/install-debian.sh
```

Si el repositorio ya está clonado, actualizar la rama y volver a instalar:

```sh
cd /opt/dvb-xtream-src
git pull --ff-only origin feat/mvp-backend
bash ./scripts/install-debian.sh
```

El instalador crea `/etc/dvb-xtream.env` con una clave aleatoria de administración. Guardar esa clave para entrar al panel en `http://IP_DEL_CONTENEDOR:8000/admin`. Ajustar `DVB_XTREAM_PUBLIC_URL` a la dirección que alcanzan los clientes. Configurar `TVH_BASE_URL`, `TVH_USERNAME` y `TVH_PASSWORD` para el servicio Tvheadend. `TVH_STREAM_PROFILE` selecciona el perfil de salida de Tvheadend; por defecto es `pass` (sin transcodificación). Para probar una salida compatible con clientes IPTV se puede usar `webtv-h264-aac-mpegts`, siempre que ese perfil exista y esté habilitado en Tvheadend. La transcodificación H.264 puede aumentar el uso de CPU; probar primero con un canal y una conexión.

## Alta de canales

En el panel se registra el UUID de canal de Tvheadend. Se puede consultar el catálogo autorizado de Tvheadend desde su API, por ejemplo `/api/channel/grid?limit=9999`. Un usuario de Tvheadend de solo lectura debe poder acceder a la reproducción. El servicio no incluye canales ni datos de acceso preconfigurados.

## Revisión del servicio

```sh
systemctl status dvb-xtream
journalctl -u dvb-xtream -f
```

El panel y las credenciales deben mantenerse en la red local o detrás de una política de acceso confiable. El servicio aún no configura TLS, firewall, EPG ni reglas de red del contenedor.

