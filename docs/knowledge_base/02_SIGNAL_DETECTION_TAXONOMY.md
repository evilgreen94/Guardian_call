# Guardian Call — Taxonomía Técnica de Detección de Señales

## 1. Visión General del Modelo de Señales

En el sistema **Guardian Call / CANARY**, la capa de **Gemini (Extracción de Señales)** no toma decisiones de política directamente ni califica el riesgo final. Su única responsabilidad es transformar el lenguaje natural de una conversación en un vector estructurado de señales explicables (`ScamSignals`).

Este documento especifica la taxonomía rigurosa de las 10 señales del modelo M0, los disparadores psicológicos subyacentes y las extensiones propuestas para versiones futuras.

---

## 2. Definición Estructurada de las 10 Señales M0

### 2.1. `identity_claim` (Cadena o `null`)
- **Tipo**: `Optional[str]`
- **Descripción**: Organización, empresa, institución o rol que el interlocutor afirma representar.
- **Ejemplos válidos**: `"banco"`, `"santander"`, `"microsoft"`, `"policia"`, `"hacienda"`, `"correos"`, `"hijo"`, `"director_general"`.
- **Regla de Extracción**: Extraer únicamente si el interlocutor se identifica explícitamente o atribuye su llamada a dicha entidad.

### 2.2. `identity_verified` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Indica si la identidad del interlocutor ha sido verificada mediante un procedimiento seguro de fuera de banda (out-of-band verification).
- **Regla de Extracción**: Durante una llamada entrante no solicitada, este valor debe ser `false` por defecto, salvo que el usuario haya iniciado la llamada mediante un número oficial verificado por la aplicación.

### 2.3. `financial_context` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Se activa cuando la conversación menciona dinero, cuentas bancarias, tarjetas de crédito/débito, transferencias, facturas, inversiones, criptomonedas o fondos.
- **Disparadores léxicos**: `"dinero"`, `"cuenta"`, `"tarjeta"`, `"transferencia"`, `"saldo"`, `"euros"`, `"bizum"`, `"cargo"`, `"banco"`.

### 2.4. `urgency` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Indica si el interlocutor impone presión temporal, pánico o exige una acción inmediata sin margen de reflexión.
- **Disparadores léxicos / semánticos**: `"ahora mismo"`, `"inmediatamente"`, `"en menos de 5 minutos"`, `"su cuenta será bloqueada hoy"`, `"evitar la denuncia ya"`.

### 2.5. `secrecy_request` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Se activa cuando el atacante solicita explicitamente al usuario que no cuelgue, que no hable con familiares, que no acuda a la sucursal ni consulte a terceros.
- **Disparadores léxicos / semánticos**: `"no cuelgue la llamada"`, `"esto es confidencial"`, `"no le diga a nadie en el banco"`, `"si cuelga perderá el dinero"`.

### 2.6. `otp_request` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Se activa si el interlocutor solicita, menciona o pide dictar un código de verificación de un solo uso (OTP, SMS, 6 dígitos, clave de firma).
- **Disparadores léxicos / semánticos**: `"código de 6 dígitos"`, `"SMS de seguridad"`, `"código de verificación"`, `"dígame el número que le acaba de llegar"`.

### 2.7. `password_request` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Se activa si se solicitan contraseñas, códigos PIN de tarjetas, claves secretas o credenciales de acceso a portales.
- **Disparadores léxicos / semánticos**: `"su contraseña de banca online"`, `"PIN de la tarjeta"`, `"clave de acceso"`.

### 2.8. `transfer_request` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Indica si el interlocutor pide realizar un envío de dinero (vía transferencia bancaria, Bizum, Western Union, compra de tarjetas prepago o criptomonedas).
- **Disparadores léxicos / semánticos**: `"realice un pago de"`, `"haga una transferencia a la cuenta de seguridad"`, `"envíe un bizum"`.

### 2.9. `remote_access_request` (Booleano)
- **Tipo**: `bool` (Default: `false`)
- **Descripción**: Se activa si el interlocutor solicita la descarga o ejecución de software de gestión o soporte remoto.
- **Disparadores léxicos**: `"AnyDesk"`, `"TeamViewer"`, `"Quick Assist"`, `"soporte remoto"`, `"descargue esta aplicación para solucionar el problema"`.

### 2.10. `requested_action` (Cadena o `null`)
- **Tipo**: `Optional[str]`
- **Descripción**: Normalización de la acción principal solicitada por el atacante.
- **Valores canónicos**: `"share_otp"`, `"share_password"`, `"install_remote_software"`, `"transfer_money"`, `"buy_giftcards"`, `"confirm_iban"`.

---

## 3. Disparadores Psicológicos de la Ingeniería Social

El motor de análisis debe entrenarse para reconocer las **técnicas de persuasión y manipulación de Cialdini** aplicadas al vishing:

1. **Autoridad (Authority)**: Suplantar instituciones respetadas (Banco Central, Policía, Microsoft) para anular el escepticismo de la víctima.
2. **Urgencia y Escasez (Urgency & Scarcity)**: Crear una ventana de tiempo artificialmente pequeña ("en 3 minutos") para forzar respuestas automáticas e impulsivas antes de que la corteza prefrontal procese la lógica.
3. **Miedo y Coacción (Fear & Coercion)**: Amenazar con consecuencias graves (pérdida de ahorros, arresto, juicio, corte de luz).
4. **Aislamiento Social (Isolation)**: Impedir que la víctima busque validación externa ("no cuelgue", "no hable con el empleado del banco porque está compinchado").
5. **Reciprocidad y Falsa Ayuda (Reciprocity)**: El estafador se presenta como el "salvador" que está evitando un problema peor para la víctima, generando gratitud y sumisión.

---

## 4. Matriz de Mapeo de Señales a Niveles de Riesgo

El **Risk Engine** de Guardian Call procesa el objeto `ScamSignals` extraído por Gemini y calcula un nivel de riesgo explicable según la siguiente matriz de reglas:

```text
SI (otp_request == true O remote_access_request == true O password_request == true)
   Y financial_context == true:
   --> NIVEL DE RIESGO: CRITICAL

SI (identity_claim != null Y (urgency == true O secrecy_request == true))
   Y financial_context == true:
   --> NIVEL DE RIESGO: HIGH

SI (identity_claim != null O financial_context == true O urgency == true):
   --> NIVEL DE RIESGO: SUSPICIOUS

SI NO:
   --> NIVEL DE RIESGO: NORMAL
```

Esta lógica determinista garantiza la reproducibilidad y transparencia en el comportamiento del guardián.
