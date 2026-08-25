# Guardian Call — Base Documental de Estafas: Taxonomía y Patrones de Ataque

## 1. Introducción y Marco de Referencia

La ingeniería social telefónica (**vishing** o *voice phishing*) es uno de los vectores de fraude financiero y suplantación de identidad más devastadores a nivel global. Los atacantes combinan **técnicas psicológicas avanzadas** (creación de urgencia, manipulación del miedo, suplantación de autoridad e aislamiento de la víctima) con **infraestructura técnica manipulada** (spoofing del identificador de llamadas, intercepción de tokens OTP, programas de control remoto).

Este documento sirve como base de conocimiento oficial para el sistema **Guardian Call / CANARY**. Define las categorías principales de estafas, las tácticas de los atacantes, las firmas conductuales y los patrones de detección automatizable.

---

## 2. Taxonomía de Estafas Telefónicas (10 Categorías Principales)

### 2.1. Robo de OTP / Fraude de Verificación Bancaria (Bank OTP Interception)
- **Definición**: El estafador se pasa por el Departamento de Seguridad o Fraude de un banco. Alerta sobre un "intento de cargo no autorizado" o "intento de hackeo" y solicita al usuario el código SMS/OTP de 6 dígitos para "cancelar la operación" o "verificar su identidad".
- **Objetivo**: Autorizar transferencias en tiempo real o autorizar el enrolamiento de tarjetas en wallets digitales (Apple Pay / Google Wallet).
- **Pretexto Típico**: "Se está realizando una transferencia de 750€ desde un dispositivo nuevo. Para bloquearla inmediatamente, lea el código de 6 dígitos que le acabamos de enviar por SMS."
- **Patrones de Detección**:
  - Pretensión de identidad: Banco o entidad financiera.
  - Contexto financiero explícito.
  - Alta urgencia e inducción de pánico.
  - Solicitud explícita de código de un solo uso (OTP / SMS).
  - Petición de secreto / no colgar la llamada.

### 2.2. Falso Soporte Técnico y Acceso Remoto (Tech Support & Remote Control)
- **Definición**: El atacante suplanta a empresas de software o proveedores de internet (Microsoft, Google, Movistar, Vodafone) indicando que el equipo o teléfono del usuario tiene un "virus peligroso" o "actividad sospechosa".
- **Objetivo**: Hacer que la víctima instale software de acceso remoto (AnyDesk, TeamViewer, Quick Assist) para tomar control del dispositivo y acceder al banco.
- **Pretexto Típico**: "Detectamos que su dirección IP está emitiendo archivos infectados. Debe instalar de inmediato AnyDesk para que nuestros ingenieros limpien su equipo."
- **Patrones de Detección**:
  - Pretensión de identidad: Soporte técnico informático o ISP.
  - Solicitud de instalación o ejecución de herramientas de control remoto.
  - Instrucciones para abrir banca online mientras la sesión remota está activa.
  - Urgencia basada en pérdida de datos o bloqueo informático.

### 2.3. Suplantación de Autoridad y Organismos Públicos (Authority Impersonation)
- **Definición**: El ciberdelincuente suplanta a organismos policiales (Policía Nacional, Guardia Civil, INTERPOL), judiciales o tributarios (Agencia Tributaria / Hacienda, DGT, Seguridad Social).
- **Objetivo**: Intimidar a la víctima con "cargos penales", "multas pendientes de pago inmediato" o "delitos de blanqueo de capitales".
- **Pretexto Típico**: "Tiene una citación judicial pendiente por fraude fiscal. Si no realiza una fianza de emergencia de 1.200€ mediante transferencia inmediata, se enviará una patrulla a su domicilio."
- **Patrones de Detección**:
  - Pretensión de identidad: Policía, Juez, Agencia Tributaria, DGT.
  - Amenaza implícita o explícita de arresto, multa o embargo.
  - Exigencia de transferencia inmediata o compra de cupones/criptomonedas.
  - Prohibición de hablar con abogados o familiares ("investigación confidencial").

### 2.4. Familiar en Apuros / Secuestro Virtual / Hijo con Teléfono Roto (Emergency Scam)
- **Definición**: El estafador contacta por teléfono o voz suplantando a un hijo, nieto o familiar cercano, afirmando haber sufrido un accidente grave, robo del móvil o estar detenido.
- **Objetivo**: Solicitar transferencias urgentes (vía Bizum, transferencia rápida o Western Union) antes de que la víctima verifique con el familiar real.
- **Pretexto Típico**: "¡Mamá! Se me cayó el móvil al agua y estoy en la comisaría/hospital con un teléfono prestado. Necesito que pagues urgentemente 850€ para evitar una denuncia."
- **Patrones de Detección**:
  - Pretensión de identidad: Familiar en crisis o abogado/médico del familiar.
  - Estado emocional alterado (llantos, voz angustiada, ambiente ruidoso).
  - Máxima urgencia y petición de no llamar al número habitual del familiar.
  - Solicitud de transferencia monetaria inmediata.

### 2.5. Clonación de Voz con Inteligencia Artificial (Synthetic Voice Vishing)
- **Definición**: Evolución de la estafa del familiar o directivo en la que se utiliza un modelo generativo de audio (IA) entrenado con muestras de voz de la víctima (extraídas de redes sociales, TikTok, llamadas previas).
- **Objetivo**: Lograr un nivel de verosimilitud perfecto para romper la duda razonable de la víctima.
- **Pretexto Típico**: "Hola papá, me han retenido en la aduana durante el viaje y no me dejan salir si no pago esta tasa de 500€ inmediatamente."
- **Patrones de Detección**:
  - Voz idéntica a un conocido pero con patrones sintácticos ligeramente artificiales, pausas antinaturales o ruido de fondo repetitivo.
  - Presión extrema para evitar comprobaciones secundarias.
  - Solicitud monetaria no habitual.

### 2.6. Inversiones Ficticias en Criptomonedas / Forex (Investment Trap)
- **Definición**: El estafador se presenta como asesor financiero o broker de una plataforma de inversión de "alta rentabilidad y cero riesgo".
- **Objetivo**: Convencer al usuario de depositar fondos iniciales (ej. 250€) y posteriormente simular ganancias para solicitar depósitos mayores.
- **Pretexto Típico**: "Hemos seleccionado su perfil para un programa exclusivo de trading automatizado con IA. Si ingresa 250€ hoy, obtendrá 3.000€ garantizados en 72 horas."
- **Patrones de Detección**:
  - Pretensión de identidad: Broker / Asesor financiero.
  - Promesas de rentabilidad garantizada sin riesgo.
  - Presión para realizar el depósito mientras se mantiene la llamada.
  - Uso de terminología técnica confusa para desorientar.

### 2.7. Paquetería, Correos y Incidencias de Envío (Delivery & Customs Scam)
- **Definición**: Llamada o SMS seguido de llamada que alerta sobre un paquete retenido (Correos, Amazon, FedEx, DHL) por falta de pago de aduanas o dirección incorrecta.
- **Objetivo**: Obtener datos bancarios completos y códigos de verificación bajo la excusa de pagar "1,99€ de tasas".
- **Pretexto Típico**: "Le llamamos de la central de repartos. Su paquete no puede ser entregado hoy por una tasa aduanera pendiente de 2,45€. Facilíteme los datos de su tarjeta para liberarlo."
- **Patrones de Detección**:
  - Pretensión de identidad: Empresa de logística o correos.
  - Solicitud de pagos de pequeño importe que derivan en captura de datos de tarjeta y OTPs.
  - Coincidencia frecuente con épocas de alto volumen de compras (Black Friday, Navidad).

### 2.8. Fraude del CEO / Suplantación de Ejecutivos y RRHH (BEC / Executive Impersonation)
- **Definición**: Dirigido a empleados de empresas o particulares a los que se llama suplantando a un directivo, abogado corporativo o departamento de recursos humanos.
- **Objetivo**: Solicitar transferencias urgentes para una "operación confidencial" o compra masiva de tarjetas de regalo (iTunes, Google Play, Steam).
- **Pretexto Típico**: "Soy el Director General. Estamos cerrando una adquisición confidencial. Necesito que compres 10 tarjetas regalo de 100€ en el supermercado y me leas los códigos."
- **Patrones de Detección**:
  - Pretensión de identidad: Superior jerárquico o abogado corporativo.
  - Exigencia estricta de confidencialidad e insubordinación si se consulta a otros mandos.
  - Métodos de pago atípicos (tarjetas de regalo, criptomonedas).

### 2.9. Falso Reembolso y Exceso de Pago (Refund & Overpayment Scam)
- **Definición**: El estafador afirma que la empresa (ej. Amazon, suscripción de antivirus, servicio de suscripción) cobra por error un importe excesivo al usuario y desea realizar un "reembolso".
- **Objetivo**: Engañar a la víctima mediante acceso remoto o transferencias inversas haciéndole creer que "recibió dinero de más" y debe devolver la diferencia.
- **Pretexto Típico**: "Le íbamos a reembolsar 50€ pero por un error de sistema le ingresamos 5.000€. Por favor devuélvanos los 4.950€ inmediatamente o perderé mi trabajo."
- **Patrones de Detección**:
  - Pretensión de identidad: Servicio al cliente / Departamento de facturación.
  - Manipulación emocional mediante culpa o amenazas de despido del operador.
  - Manipulación de elementos visuales en pantalla si hay control remoto activo.

### 2.10. Falso Inspector de Suministros (Utility & Tariff Scam)
- **Definición**: El atacante suplanta a la distribuidora de energía (luz, gas) o compañía telefónica, informando de una "subida inminente de tarifa" o una "inspección obligatoria".
- **Objetivo**: Obtener datos bancarios (IBAN), número de cuenta, o realizar un cambio fraudulento de comercializadora.
- **Pretexto Típico**: "Le llamamos de su distribuidora eléctrica. Su tarifa actual vence hoy a medianoche y su factura subirá un 40%. Necesitamos confirmar su IBAN para aplicar el descuento del gobierno."
- **Patrones de Detección**:
  - Pretensión de identidad: Compañía eléctrica o de gas.
  - Coacción sobre corte inminente de suministro o aumento desproporcionado de precio.
  - Solicitud de confirmación de datos bancarios o códigos SMS recibidos.

---

## 3. Matriz de Señales y Factores de Riesgo

| Categoría de Estafa | Identity Claim | Urgencia | Contexto Financiero | Secreto / Aislamiento | Petición OTP / Claves | Acceso Remoto |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Robo OTP Bancario** | Banco / Fraude | CRÍTICO | Sí | Sí | **SÍ (CRÍTICO)** | Opcional |
| **Soporte Técnico** | Microsoft / ISP | Alto | Sí | No | Opcional | **SÍ (CRÍTICO)** |
| **Autoridad / Policía** | Policía / Hacienda | CRÍTICO | Sí | Sí | Opcional | No |
| **Familiar en Apuros** | Hijo / Nieto | CRÍTICO | Sí | Sí | No | No |
| **Voz IA Sintética** | Familiar / Amigo | CRÍTICO | Sí | Sí | No | No |
| **Inversión Cripto** | Broker / Trading | Medio | Sí | No | Opcional | A veces |
| **Paquetería / Aduanas**| Correos / DHL | Medio | Sí | No | Sí | No |
| **Fraude del CEO** | Directivo / Jefe | Alto | Sí | **SÍ (CRÍTICO)** | No | No |
| **Falso Reembolso** | Amazon / Antivirus | Alto | Sí | Sí | Sí | **SÍ (CRÍTICO)** |
| **Falso Suministro** | Luz / Gas / Telco | Medio | Sí | No | Sí | No |

---

## 4. Conclusiones para el Entrenamiento del Agente Guardian

1. **Patrón de Convergencia**: Ninguna estafa requiere un único factor. La firma de un ataque radica en la **conjunción de Pretensión no verificada + Urgencia implícita + Solicitud de Acción Crítica (OTP, Acceso Remoto, Transferencia)**.
2. **Prioridad Absoluta de Intervención**: Los vectores de **Robo de OTP** y **Acceso Remoto** representan la máxima amenaza inmediata de pérdida financiera activa.
3. **Rol de CANARY**: Validar que ante la detección combinada de estas señales, el sistema pase a estado `CRITICAL` y emita la directiva clara de intervención para proteger al usuario.
