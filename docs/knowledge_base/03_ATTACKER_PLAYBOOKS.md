# Guardian Call — Manual Táctico de Ataque (Attacker Playbooks)

## 1. Ciclo de Vida del Ataque de Vishing (Lifecycle Model)

Los ciberdelincuentes profesionales ejecutan las llamadas de vishing siguiendo un **script o manual estructurado**. Comprender las fases de este ciclo de vida permite a **Guardian Call** anticiparse a la fase crítica del fraude antes de que la víctima entregue información sensible.

```text
[FASE 1: RECONOCIMIENTO] ──► [FASE 2: ENGANCHE] ──► [FASE 3: PRETEXTO] ──► [FASE 4: BLOQUEO] ──► [FASE 5: EJECUCIÓN] ──► [FASE 6: SALIDA]
```

---

## 2. Descripción Detallada de las Fases del Ataque

### Fase 1: Reconocimiento (OSINT / Data Breaches)
- **Acción del Atacante**: Obtiene previamente datos reales de la víctima (nombre, DNI, cuatro últimos dígitos de la tarjeta, operadora o banco) a partir de filtraciones de datos o redes sociales.
- **Impacto**: Le permite superar la barrera inicial de credibilidad ("Buenas tardes, ¿hablo con Carlos Pérez? Le llamo por su cuenta de Banco Santander finalizada en 4012...").

### Fase 2: Enganche e Identificación Falsa (Hook & Identity Claim)
- **Acción del Atacante**: Establece la pretensión de identidad utilizando tono profesional, lenguaje corporativo y ambiente de call center de fondo (efectos de sonido foley).
- **Señal Generada**: `identity_claim != null`.

### Fase 3: Introducción de la Crisis / Pretexto (Pretext & Emergency)
- **Acción del Atacante**: Notifica un evento alarmante que requiere atención inmediata (cargo sospechoso, multa, virus informático, familiar retenido).
- **Señales Generadas**: `financial_context = true`, `urgency = true`.

### Fase 4: Bloqueo Psicológico e Aislamiento (Psychological Lock & Isolation)
- **Acción del Atacante**: Exige al usuario no colgar la llamada bajo ningún concepto, argumentando que si cuelga perderá el dinero o se tramitará la denuncia.
- **Señales Generadas**: `secrecy_request = true`.

### Fase 5: Solicitud de la Acción Crítica / Ejecución (Critical Action Request)
- **Acción del Atacante**: Pide la entrega de la clave OTP, instalación de AnyDesk, transferencia bancaria o dictado de credenciales.
- **Señales Generadas**: `otp_request = true`, `remote_access_request = true` o `transfer_request = true`.

### Fase 6: Salida y Limpieza (Clean Exit & Delay)
- **Acción del Atacante**: Tranquiliza a la víctima indicando que "el problema ha sido resuelto" y le pide esperar 24 horas antes de revisar su cuenta para dar tiempo a que los fondos se muevan sin que se tramite la denuncia.

---

## 3. Scripts Típicos y Respuestas a Objeciones

### Playbook A: Robo de OTP Bancario (Bank Fraud Department)

**Diálogo de Ataque Típico**:
> **Atacante**: "Buenos días, le habla Sergio del departamento de seguridad de Banco Santander. Hemos detectado un intento de transferencia de 890€ desde una dirección IP no habitual en Barcelona."
> **Víctima**: "¿Cómo? Yo no he hecho ninguna transferencia."
> **Atacante**: "Exacto. Para anularla de inmediato y retener los fondos, le acabo de enviar un código de verificación de 6 dígitos por SMS a su móvil. Dictemelo para validar la cancelación."

**Manejo de Objeciones del Estafador**:
- *Si la víctima dice: "El mensaje del SMS dice que no comparta este código con nadie."*
- *Respuesta del atacante*: "Ese aviso es para llamadas no verificadas. Esta es una llamada oficial del sistema anti-fraude. Si no me da el código en los próximos 60 segundos, la transferencia de 890€ se procesará definitivamente."

---

### Playbook B: Falso Soporte Técnico de Acceso Remoto

**Diálogo de Ataque Típico**:
> **Atacante**: "Hola, le llamamos del soporte de Microsoft. Nuestro servidor central ha registrado alertas críticas de malware en su equipo Windows."
> **Víctima**: "Pero mi ordenador funciona bien..."
> **Atacante**: "El virus trabaja en segundo plano robando sus contraseñas bancarias. Entre en la página web `anydesk.com`, descargue la aplicación y dígame el código de 9 dígitos que le aparece en pantalla para que limpiemos su sistema."

**Manejo de Objeciones del Estafador**:
- *Si la víctima dice: "Prefiero llevar el equipo a una tienda local."*
- *Respuesta del atacante*: "Las tiendas locales no tienen acceso a los servidores de licencias de Microsoft. Si apaga el equipo ahora, el disco duro quedará encriptado permanentemente."

---

### Playbook C: Falsa Bóveda Segura Bancaria (Manejo Preventivo de Objeciones)

**Diálogo de Ataque Típico (Español)**:
> **Atacante**: "Hola, muy buenas tardes. Le llamo desde el Departamento de Prevención de Fraudes del Banco Santander. ¿Hablo con el señor García?"
> **Víctima**: "Sí, soy yo. ¿Qué sucede?"
> **Atacante**: "Señor García, nuestra monitorización ha bloqueado una transferencia de 3.500 euros hacia Lituania. Para su tranquilidad, le recuerdo que yo NUNCA le pediré su contraseña ni PIN. Únicamente necesitamos confirmar su identidad para cancelar la operación."
> **Víctima**: "Es que me parece raro, ¿cómo sé que usted es del banco?"
> **Atacante**: "Puede comprobar que llamo desde el número oficial impreso en su tarjeta. Pero si cuelga, el sistema liberará los 3.500 euros en 2 minutos. Para protegerlo, le envié un SMS con un enlace a su bóveda de protección."

---

### Playbook D: Falso Soporte de TI Corporativo (MFA Push Bombing / Scattered Spider)

**Diálogo de Ataque Típico (Inglés)**:
> **Attacker**: "Hi Sarah, this is Mike from Global IT Security. We are seeing anomalous login attempts trying to access your Microsoft 365 environment."
> **Victim**: "My phone has been buzzing with approval requests for the last ten minutes..."
> **Attacker**: "That confirms our telemetry. It's a credential stuffing attack. Hit 'Approve' on the very next push notification so our security backend can synchronize your device token and lock out the attacker."
> **Victim**: "Wait, training says never approve a push notification I didn't initiate!"
> **Attacker**: "You are right to follow protocol, but this is an active session hijack. If you drop this line, they will gain full access to SharePoint. Just hit approve on this single prompt so I can isolate your container."


---

## 4. Estrategia de Intervención de Guardian Call

Cuando Guardian Call detecta la progresión del ataque hacia la **Fase 5 (Ejecución)**:

1. **Interrupción Visual**: Muestra la pantalla de advertencia simplificada en el móvil del usuario:
   ```text
   POSIBLE ESTAFA
   NO DIGA ESE CÓDIGO
   NO REALICE TRANSFERENCIAS
   ```
2. **Notificación al Círculo de Confianza**: Si la política Canary está configurada para nivel `CRITICAL`, envía una alerta SMS/Push a los contactos de confianza configurados.
3. **Recomendación de Fin de Llamada**: Sugiere al usuario pulsar el botón de finalizar llamada inmediatamente y contactar con la entidad oficial.
