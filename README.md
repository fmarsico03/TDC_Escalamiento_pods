# Control de latencia de un Microservicio mediante escalado de pods

**Trabajo Práctico Integral — Tecnologías para la Automatización**  
UTN FRBA · Curso K4052 · 1° Cuatrimestre 2026  
Alumno: Franco Alessandro Marsico · Profesor: Drando. Omar Civale

---

## Descripción

Simulación interactiva de un lazo de control en tiempo real que regula la **latencia de respuesta de un microservicio** ajustando automáticamente la cantidad de réplicas (pods) en Kubernetes. El sistema modela el comportamiento del HPA (Horizontal Pod Autoscaler) usando los conceptos de la Teoría de Control: controlador PI, proceso de primer orden, perturbaciones de carga y realimentación negativa.

---

## Modelo de control

```
         e(t)                    u (pods)            d (carga)
L_ref ──►(+)──► C(s) ──► A(s) ──────►(+)──► G(s) ──►(+)──► L(t)
          ▲─────────────── H(s) ◄──────────────────────────────┘
               (Prometheus)
```

| Elemento | Implementación | Función de transferencia |
|---|---|---|
| Referencia `L_ref` | Latencia objetivo (escalón) | — |
| Controlador `C(s)` | PI — proporcional + integral | `Kp + Ki/s` |
| Actuador `A(s)` | Kubernetes HPA, Ka = 1 | `Ka = 1` |
| Proceso `G(s)` | Microservicio 1er orden | `K / (T·s + 1)` |
| Perturbación `Gd(s)` | Variación de carga (req/s) | `Kd / (T·s + 1)` |
| Sensor `H(s)` | Prometheus (ideal) | `H = 1` |

### Parámetros del proceso

| Parámetro | Valor | Significado |
|---|---|---|
| `K` | 10 ms/pod | Ganancia estática del proceso |
| `T` | 60 s | `T_scrape + T_reconcile + T_coldstart` |
| `T_scrape` | 15 s | Intervalo de muestreo de Prometheus |
| `T_reconcile` | 15 s | Ciclo de reconciliación del HPA |
| `T_coldstart` | 30 s | Arranque de un pod nuevo |
| `Kd` | 0.5 ms·s/req | Ganancia de la perturbación de carga |
| `L0` | 200 ms | Latencia base nominal |
| `POD_MIN / MAX` | 1 / 30 | Límites del actuador (saturación) |
| `TARGET_BAND` | ±15 ms | Banda de error aceptable alrededor de la referencia |

### Tipo de sistema y error en estado estable

La acción integral del controlador PI convierte el sistema en **tipo 1**, lo que garantiza error nulo en estado estable ante entrada escalón:

```
E_ss = 0
```

### Acción inversa

Agregar pods **reduce** la latencia (relación inversa). La inversión se concentra una sola vez en el mapeo `pods = clamp(round(-u), POD_MIN, POD_MAX)`, permitiendo que las ecuaciones del proceso mantengan signo positivo y que el lazo cierre con realimentación negativa convencional.

---

## Estructura del proyecto

```
TDC_Escalamiento_pods/
├── control.py           # Motor de simulación: PIController, MicroserviceModel, Simulation, History
├── simulacion.py        # Interfaz gráfica interactiva (CustomTkinter + Matplotlib)
├── batch_simulacion.py  # Simulación headless por lotes: genera métricas y PNG sin GUI
├── utils.py             # Utilidades: clamp()
└── requirements.txt     # Dependencias Python
```

### `control.py`
Motor del lazo cerrado. Contiene:
- `PIController` — controlador PI discreto con acumulación real del integrador.
- `MicroserviceModel` — proceso de primer orden discretizado por ZOH (`L[k] = L[k-1] + K·Δu·(1-e^(-T/τ)) + Kd·Δd·(1-e^(-T/τ))`).
- `Simulation` — ensambla el lazo completo y avanza un paso por llamada a `update()`.
- `History` — buffer rodante de 400 puntos para graficar.

### `simulacion.py`
GUI en tiempo real construida con CustomTkinter y Matplotlib embebido. Permite:
- Ajustar `Kp` y `Ki` con sliders en vivo.
- Cambiar la referencia de latencia (100–400 ms).
- Aplicar perturbaciones de carga continuas o en escalón (+30 req/s).
- Pausar, resetear y guardar el gráfico como PNG al cerrar.

### `batch_simulacion.py`
Script headless para correr simulaciones sin interfaz gráfica. Útil para generar resultados reproducibles desde la terminal. Permite:
- Configurar `Kp`, `Ki`, `Lref` y duración total directamente en el código.
- Definir una lista de eventos de carga `(tiempo_s, carga_req/s)` para modelar perturbaciones.
- Imprimir métricas por consola: latencia máxima, error en estado estable, sobreimpulso y rango de pods.
- Guardar el gráfico de 4 paneles como PNG (`simulacion_latencia.png`).

### `utils.py`
Funciones auxiliares sin dependencias externas (`clamp`).

---

## Instalación y ejecución

**Requisitos:** Python 3.9+

```bash
pip install -r requirements.txt
```

### Modo interactivo (GUI)

```bash
python simulacion.py
```

### Modo batch (sin GUI)

```bash
python batch_simulacion.py
```

Editar las constantes al inicio de `main()` para cambiar el escenario:

```python
KP       = 0.1
KI       = 0.025
LREF     = 200.0    # ms
DURATION = 600.0    # s
LOAD_EVENTS = [(0, 60)]  # (tiempo_s, carga_req/s)
```

### Dependencias

| Librería | Versión mínima | Uso |
|---|---|---|
| `customtkinter` | 5.2.0 | GUI moderna sobre Tkinter |
| `matplotlib` | 3.7.0 | Gráficos en tiempo real embebidos |

---

## Interfaz gráfica

La ventana se divide en un panel de controles (izquierda) y cuatro gráficos en tiempo real (derecha):

1. **Latencia (ms)** — variable controlada y referencia, con banda de tolerancia ±15 ms sombreada.
2. **Error (ms)** — diferencia entre referencia y latencia medida.
3. **Réplicas (pods)** — acción de control del actuador (escalera discreta).
4. **Carga (req/s)** — perturbación externa aplicada al proceso.

El panel lateral muestra los valores instantáneos y el estado `EN BANDA / FUERA DE BANDA`.

**Controles disponibles:**

| Control | Función |
|---|---|
| Slider `Kp` | Ganancia proporcional (0 – 0.5) |
| Slider `Ki` | Ganancia integral (0 – 0.1) |
| Slider `Referencia` | Latencia objetivo en ms (100 – 400) |
| Slider `Carga` | Perturbación sostenida en req/s (0 – 300) |
| Botón `Escalón de carga` | Aplica +30 req/s de perturbación instantánea |
| Botón `Pausa / Reanudar` | Congela la simulación |
| Botón `Reset` | Restaura condiciones iniciales |
| Botón `Cerrar` / `Esc` | Cierra y ofrece guardar PNG |

---

## Parámetros por defecto

| Parámetro | Valor inicial |
|---|---|
| `Kp` | 0.1 |
| `Ki` | 0.025 |
| Referencia | 200 ms |
| Carga | 0 req/s |
| Paso de integración `DT` | 15 s |
| Refresco de pantalla | 50 ms |
| Ventana visible | 600 s |
