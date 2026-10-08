# DVB-Xtream

Panel local para recibir y distribuir canales DVB-S/S2 con acceso compatible con Xtream Codes, sustituyendo el motor Astra por componentes de software libre.

## Objetivos

- Recibir canales desde sintonizadores TBS DVB-S/S2.
- Administrar canales, categorías y EPG desde una sola interfaz local.
- Permitir inicio de sesión de clientes en apps compatibles con Xtream Codes API.
- Administrar vencimiento, límite de conexiones simultáneas y estado de cada cuenta.
- Entregar el flujo directamente desde el servidor de TV, sin transcodificar por defecto.
- Incluir un instalador reproducible para un contenedor limpio Debian 13 en Proxmox.

## Arquitectura inicial

- **Recepción DVB y salida de TV:** Tvheadend, sujeto a validar el modelo exacto de la TBS libre y la compatibilidad de recepción.
- **Panel y API Xtream:** servicio local de este proyecto para cuentas, categorías, EPG y compatibilidad con las apps cliente.
- **Pruebas:** contenedor Debian 13 de desarrollo con la TBS libre. Astra continuará atendiendo los sintonizadores actuales durante el piloto.
- **Instalación final:** instalador del repositorio para desplegar en otro contenedor Debian 13 limpio.

## Principios

- Mantener la recepción de canales de TV sin transcodificación salvo que se solicite.
- No modificar el contenedor de producción durante el desarrollo.
- No guardar contraseñas, tokens, URLs privadas ni datos de clientes en el repositorio.
- Mantener el panel accesible en la red local; la exposición externa se configurará aparte si se requiere.

## Estado

Repositorio recién iniciado. La integración DVB real depende de identificar la TBS de prueba y pasar sus dispositivos al contenedor de desarrollo.
