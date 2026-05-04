# Acceso VPN para Trabajo Remoto

## Requisitos
- Cliente VPN "FortiClient" instalado.
- Credenciales de dominio activas.
- Token de autenticación multifactor (Duo Mobile).

## Configuración del Servidor
- **URL**: vpn.empresa.com
- **Puerto**: 443
- **Certificado**: Certificado de confianza de la empresa (se instala automáticamente con el cliente).

## Solución de Problemas (Troubleshooting)
1. **Error de Conexión**: Verifique que su conexión a internet esté activa y que no haya firewalls locales bloqueando el puerto 443.
2. **Error de Credenciales**: Las contraseñas de red deben cambiarse cada 90 días. Asegúrese de que su cuenta no esté bloqueada.
3. **Pérdida de Conexión**: La sesión de la VPN se cierra automáticamente después de 8 horas de inactividad.
