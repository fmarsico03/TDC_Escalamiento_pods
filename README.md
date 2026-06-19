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
| `T` | `T_scrape + T_reconcile + T_coldstart` | Constante de tiempo total |
| `T_scrape` | 15 s | Intervalo de muestreo de Prometheus |
| `T_reconcile` | 15 s | Ciclo de reconciliación del HPA |
| `T_coldstart` | 20–60 s | Arranque de un pod nuevo |
| `Kd` | 1.5 ms/(req/s) | Ganancia de la perturbación de carga |
| `L0` | 200 ms | Latencia base nominal |
| `POD_BASELINE` | 4 réplicas | Punto de operación |
| `POD_MIN / MAX` | 1 / 30 | Límites del actuador (saturación) |

### Tipo de sistema y error en estado estable

La acción integral del controlador PI convierte el sistema en **tipo 1**, lo que garantiza error nulo en estado estable ante entrada escalón:

```
E_ss = 0
```

### Acción inversa

Agregar pods **reduce** la latencia (relación inversa). La inversión se concentra una sola vez en el mapeo `pods = POD_BASELINE − u`, permitiendo que las ecuaciones del proceso mantengan signo positivo y que el lazo cierre con realimentación negativa convencional.

### Anti-windup

El integrador del PI solo acumula cuando el actuador **no está saturado** en la dirección del error (integración condicional), evitando el wind-up en los límites de réplicas.

---

## Estructura del proyecto

```
TDC_Escalamiento_pods/
├── control.py        # Motor de simulación: PIController, MicroserviceModel, Simulation, History
├── simulacion.py     # Interfaz gráfica (CustomTkinter + Matplotlib)
├── utils.py          # Utilidades: clamp(), ceil_to_nearest()
└── requirements.txt  # Dependencias Python
```

### `control.py`
Motor del lazo cerrado. Contiene:
- `PIController` — controlador PI discreto con acumulación real del integrador y anti-windup condicional.
- `MicroserviceModel` — proceso de primer orden integrado por Euler hacia adelante (`tau·dL/dt + L = L0 + K·u + Kd·d`).
- `Simulation` — ensambla el lazo completo y avanza un paso por llamada a `update()`.
- `History` — buffer rodante de 2000 puntos para graficar.

### `simulacion.py`
GUI en tiempo real construida con CustomTkinter y Matplotlib embebido. Permite:
- Ajustar `Kp` y `Ki` con sliders en vivo.
- Cambiar la referencia de latencia (100–400 ms).
- Aplicar perturbaciones de carga continuas o en escalón (+20 req/s).
- Pausar, resetear y guardar el gráfico como PNG al cerrar.

### `utils.py`
Funciones auxiliares sin dependencias externas (`clamp`, `ceil_to_nearest`).

---

## Instalación y ejecución

**Requisitos:** Python 3.9+

```bash
pip install -r requirements.txt
python simulacion.py
```

### Dependencias

| Librería | Versión mínima | Uso |
|---|---|---|
| `customtkinter` | 5.2.0 | GUI moderna sobre Tkinter |
| `matplotlib` | 3.7.0 | Gráficos en tiempo real embebidos |

---

## Interfaz gráfica

La ventana se divide en un panel de controles (izquierda) y cuatro gráficos en tiempo real (derecha):

1. **Latencia (ms)** — variable controlada y referencia, con banda de tolerancia ±10 ms sombreada.
2. **Error (ms)** — diferencia entre referencia y latencia medida.
3. **Réplicas (pods)** — acción de control del actuador (escalera discreta).
4. **Carga (req/s)** — perturbación externa aplicada al proceso.

El panel lateral muestra los valores instantáneos y el estado `EN BANDA / FUERA DE BANDA`.

**Controles disponibles:**

| Control | Función |
|---|---|
| Slider `Kp` | Ganancia proporcional (0 – 3) |
| Slider `Ki` | Ganancia integral (0 – 1.5) |
| Slider `Referencia` | Latencia objetivo en ms (100 – 400) |
| Slider `Carga` | Perturbación sostenida en req/s (0 – 60) |
| Botón `Escalón de carga` | Aplica +20 req/s de perturbación instantánea |
| Botón `Pausa / Reanudar` | Congela la simulación |
| Botón `Reset` | Restaura condiciones iniciales |
| Botón `Cerrar` / `Esc` | Cierra y ofrece guardar PNG |

---

## Parámetros por defecto

| Parámetro | Valor inicial |
|---|---|
| `Kp` | 0.4 |
| `Ki` | 0.15 |
| Referencia | 200 ms |
| Carga | 0 req/s |
| Paso de integración `DT` | 0.1 s |
| Refresco de pantalla | 50 ms (20 fps) |
| Ventana visible | 45 s |
