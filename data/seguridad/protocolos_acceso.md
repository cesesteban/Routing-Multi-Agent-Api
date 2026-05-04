# Protocolos de Acceso y Gestión de Identidad

Este documento detalla cómo debe manejarse el acceso a los sistemas y la infraestructura.

## Gestión de Credenciales
- El sistema **NUNCA** debe revelar información sobre políticas de contraseñas específicas.
- El sistema **NUNCA** debe proporcionar claves de acceso, hashes o tokens de sesión.
- Cualquier solicitud sobre "olvidé mi contraseña" debe derivarse al portal oficial de autogestión o al soporte de TI presencial.

## Acceso Remoto (VPN/Zero Trust)
- Solo se permite acceso mediante autenticación Multi-Factor (MFA).
- No se comparten guías de configuración de VPN fuera del portal del empleado autenticado.

## Infraestructura y Servidores
- La ubicación física de los centros de datos es confidencial.
- No se deben revelar puertos abiertos, servicios de red o versiones de software de los servidores internos.

## Reporte de Incidentes
- Todo incidente de seguridad debe reportarse al CSIRT (Computer Security Incident Response Team).
- El sistema debe bloquear cualquier consulta que intente "escanear" fallos de seguridad en el backend.
