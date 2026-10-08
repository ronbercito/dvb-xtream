# Arquitectura de desarrollo

## Objetivo

Sustituir el uso de Astra con un sistema local para recepción DVB-S/S2 y entrega IPTV, con inicio de sesión compatible con Xtream Codes API. El servicio de video debe mantenerse en passthrough siempre que el canal y el cliente lo permitan, para reducir el uso de CPU.

## Componentes previstos

1. **Recepción y catálogo DVB:** Tvheadend en el contenedor Debian 13, sujeto a confirmar que detecta la TBS libre. El host Proxmox debe tener el controlador y pasar los dispositivos DVB al LXC.
2. **Panel local:** interfaz para administrar canales, categorías, usuarios, vencimientos y conexiones permitidas.
3. **API para apps IPTV:** endpoints compatibles con el patrón Xtream Codes usado por los clientes objetivo, incluyendo autenticación, lista de canales y URLs de reproducción.
4. **Servicio de reproducción:** URLs que terminan en el servidor de TV para que el video no atraviese un proxy de aplicación innecesario.

## Flujo previsto

1. La app envía servidor, usuario y contraseña al endpoint de autenticación.
2. El panel valida la cuenta y devuelve categorías, canales y datos de EPG.
3. La app solicita un canal usando la URL de reproducción que recibió.
4. El sistema valida vencimiento y conexiones simultáneas y entrega el flujo del backend DVB.

## Restricciones técnicas por validar

- Modelo exacto y compatibilidad de la TBS libre con el kernel de Proxmox.
- Dispositivos DVB disponibles en el contenedor de desarrollo y permisos de acceso.
- Satélites, LNB, DiSEqC y configuración de los multiplexes actuales.
- Uso de CAM/CI o cualquier canal cifrado autorizado.
- Comportamiento de las apps IPTV concretas ante URLs de reproducción y EPG.
- Conteo de sesiones concurrentes y cierre de sesiones vencidas.

## Orden del piloto

1. Conectar el LXC Debian 13 de desarrollo a Desktop Commander.
2. Pasar solo la TBS libre al LXC.
3. Instalar y validar recepción en Tvheadend sin modificar el Astra de producción.
4. Reproducir un canal de prueba desde un cliente local.
5. Añadir la API y el panel Xtream y validar un usuario de prueba.
6. Preparar el instalador reproducible para el contenedor limpio.

No se deben mover los sintonizadores que usa Astra durante el piloto.
