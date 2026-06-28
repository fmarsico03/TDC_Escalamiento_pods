# Control de latencia de un Microservicio mediante escalado de pods

## Descripción

Simulación interactiva de un lazo de control en tiempo real que regula la **latencia de respuesta de un microservicio** ajustando automáticamente la cantidad de réplicas (pods) en Kubernetes. El sistema modela el comportamiento del HPA (Horizontal Pod Autoscaler) usando los conceptos de la Teoría de Control: controlador PI, proceso de primer orden, perturbaciones de carga y realimentación negativa.

---


## Instalación y ejecución

**Requisitos:** Python 3.9+

```bash
pip install -r requirements.txt
```
## Estructura del proyecto
```
TDC_Escalamiento_pods/
├── control.py           # Motor de simulación: PIController, MicroserviceModel, Simulation, History
├── simulacion.py        # Interfaz gráfica interactiva (CustomTkinter + Matplotlib)
├── batch_simulacion.py  # Simulación headless por lotes: genera métricas y PNG sin GUI
├── utils.py             # Utilidades: clamp()
└── requirements.txt     # Dependencias Python
```

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


### Modo interactivo (GUI)

```bash
python simulacion.py
```

### Modo batch (sin GUI)

```bash
python batch_simulacion.py
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
