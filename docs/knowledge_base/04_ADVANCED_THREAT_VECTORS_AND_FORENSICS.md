# Guardian Call — Vectores Avanzados de Amenaza y Análisis Acústico Forense

## 1. El Modelo STAM (Synthetic Trust Attack Model)

El **Modelo de Ataque de Confianza Sintética (STAM)** describe la arquitectura operativa de 8 etapas utilizada por grupos avanzados de ciberdelincuencia (como *Scattered Spider / UNC3944*) para construir credibilidad sintética y forzar la toma de decisiones en segundos.

```text
[1. RECONOCIMIENTO OSINT] ──► [2. PERTURBACIÓN INICIAL] ──► [3. ANCLAJE DE AUTORIDAD] ──► [4. PRETEXTO CONTEXTUAL]
                                                                                                  │
[8. EXFILTRACIÓN Y SALIDA] ◄── [7. ACCIÓN PERJUDICIAL] ◄── [6. COMPRESIÓN DE DECISIÓN] ◄── [5. FATIGA Y PRESIÓN]
```

### La Etapa 6: Compresión de la Decisión (Decision Compression)
Bajo presión temporal extrema y alta carga emocional, el cerebro humano pasa involuntariamente de la cognición analítica (Sistema 2 de Kahneman) a la reacción automática (Sistema 1). El estafador inyecta simultáneamente urgencia, autoridad e instrucciones técnicas complejas para colapsar la capacidad de verificación del usuario.

---

## 2. Vectores Emergentes de Evasión de MFA

### 2.1. MFA Push Fatigue / Push Bombing
- **Mecanismo**: El atacante obtiene credenciales corporativas primarias en la dark web o mediante infostealers y desencadena decenas de solicitudes Push de autenticación de forma continua en el móvil de la víctima.
- **Acción en la Llamada**: Simultáneamente, llama haciéndose pasar por el soporte de TI corporativo, afirmando que el bombardeo de notificaciones se debe a un "ataque externo" o "sincronización de token", e instruye a la víctima a pulsar **"Aprobar"** en la siguiente notificación para "bloquear la amenaza".
- **Firma de Detección**: `identity_claim = "soporte_tecnico"`, `urgency = true`, `otp_request = true`, `requested_action = "approve_mfa_push"`.

### 2.2. Phishing de Códigos de Dispositivo OAuth (OAuth Device Code Phishing)
- **Mecanismo**: El atacante inicia un flujo de autorización en servicios cloud (Microsoft 365, Google Workspace) mediante `microsoft.com/devicelogin` y obtiene un código alfanumérico.
- **Acción en la Llamada**: Llama a la víctima y la guía para que introduzca ese código en la página oficial de autenticación. Al hacerlo, la víctima autoriza silenciosamente el acceso del dispositivo del atacante a su cuenta sin revelar su contraseña.

---

## 3. Análisis Acústico Forense de Deepfakes de Voz (IA Generativa)

Las voces clonadas por IA generativa en tiempo real (con latencias inferiores a 600 ms) son perceptualmente indistinguibles para el oído humano. Sin embargo, dejan **huellas digitales en el dominio espectral**:

### 3.1. Ausencia de Micro-variaciones Biomecánicas (Jitter y Shimmer)
- **Voz Humana Genuina**: Presenta pequeñas variaciones biomecánicas inestables en la frecuencia fundamental (*jitter*) y fluctuaciones microscópicas de amplitud (*shimmer*).
- **Voz Sintética / IA**: Tiende a ser matemáticamente "demasiado perfecta", con valores de *jitter* y *shimmer* antinaturalmente estables o planos.

### 3.2. Artefactos de Vocoders Neuronales
- **Transformada Rápida de Fourier (STFT) y Mel-Espectrogramas**: El análisis espectral revela cortes de energía abruptos en frecuencias superiores a 7.8 kHz, patrones de bandas repetitivas en el espectrograma que no se corresponden con el tracto vocal humano y discontinuidades armónicas.
- **Identificación MFCC (Coeficientes Cepstrales en Frecuencia Mel)**: Extracción de vectores de características para clasificar entre voz biológica y voz sintética.

---

## 4. Estrategia Defensiva de Guardian Call

Cuando Guardian Call detecta la conjunción de señales semánticas peligrosas junto con artefactos acústicos de voz sintética o presión de fatiga MFA, la directiva inmediata emitida es:

```text
CUELGUE Y VERIFIQUE POR CANAL OFICIAL
```
