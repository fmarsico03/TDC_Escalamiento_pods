"""
Motor de simulación del lazo de control de latencia de un microservicio
mediante escalado automático de réplicas (modelo del HPA de Kubernetes).

Mapeo con el documento del TFI:
    - Variable controlada : latencia L(t)        [ms]
    - Acción de control   : réplicas (pods)      [u]
    - Perturbación        : carga de requests d  [req/s]
    - Referencia          : latencia objetivo L_ref (escalón)
    - Controlador C(s)    : PI -> Kp + Ki/s
    - Actuador A(s)       : Kubernetes, ganancia pura Ka = 1
    - Proceso G(s)        : 1er orden, tau*dL/dt + L = L0 + K*u + Kd*d
    - Sensor H(s)         : Prometheus, ideal (H = 1)
"""

import math

from utils import clamp

# --- Constantes ---

## Paso de integración
DT = 15.0                   # (s)  paso de simulación = T_scrape

## Proceso (microservicio)
TAU = 60.0                  # (s)  constante de tiempo del proceso
L0 = 200.0                  # (ms) latencia referencia
K = 10.0                    # (ms/pod) ganancia estática del proceso
KD = 0.5                    # (ms·s/req) ganancia de la perturbación

## Actuador (Kubernetes)
POD_MIN = 1                 # mínimo de réplicas
POD_MAX = 30                # máximo de réplicas (saturación del actuador)

## Banda objetivo / condición de falla
TARGET_BAND = 30.0          # (ms) Banda de error aceptable


## Historia (buffer de ploteo)
POINTS_OF_HISTORY = 400


class PIController:
    """Controlador PI discreto con integrador real (acumulativo)."""

    def __init__(self, Kp, Ki):
        self.Kp = Kp
        self.Ki = Ki
        self.integral = 0.0

    def compute(self, error):
        """Devuelve (u, termino_P, termino_I)."""
        self.integral += error * DT
        p_term = self.Kp * error
        i_term = self.Ki * self.integral
        return p_term + i_term, p_term, i_term

    def reset_gains(self, Kp, Ki):
        self.Kp = Kp
        self.Ki = Ki
        self.integral = 0.0


class MicroserviceModel:
    """Proceso de primer orden (ZOH a T_scrape):
    L[k] = L[k-1] + K·Δu·(1-e^(-T_scrape/τ)) + Kd·Δd·(1-e^(-T_scrape/τ))"""

    def __init__(self):
        self.latency = L0
        self._prev_u = -float(POD_MIN)
        self._prev_load = 0.0

    def update(self, u, load):
        factor = 1.0 - math.exp(-DT / TAU)
        delta_u = u - self._prev_u
        delta_d = load - self._prev_load
        self.latency += (K * delta_u + KD * delta_d) * factor
        self._prev_u = u
        self._prev_load = load
        return self.latency

    def reset(self):
        self.latency = L0
        self._prev_u = -float(POD_MIN)
        self._prev_load = 0.0


class Simulation:
    """Arma el lazo cerrado completo y avanza un paso por llamada a update()."""

    def __init__(self, kp, ki, reference, load=0.0):
        self.pid = PIController(kp, ki)
        self.process = MicroserviceModel()
        self.history = History()
        self.reference = reference     # (ms) latencia objetivo L_ref
        self.load = load               # (req/s) carga sostenida (perturbación de escalón)
        self.time = 0.0

    def update(self):
        feedback = self.process.latency
        error = self.reference - feedback          # e = L_ref - f  (realim. negativa)

        # 2. Controlador PI.
        u, p_term, i_term = self.pid.compute(error)

        # 3. Actuador (Ka = 1): u -> cantidad de pods (cuantos pods me faltan).
        pods = clamp(int(round(-u)), POD_MIN, POD_MAX)
        u_eff = -float(pods)               # acción efectivamente aplicada tras saturar

        # 4. Proceso: la planta responde a la acción efectiva y a la carga.
        latency = self.process.update(u_eff, self.load)

        # 5. Registro.
        in_band = abs(latency - self.reference) <= TARGET_BAND
        self.history.log(self.time, latency, error, u_eff, pods,
                         self.load, self.reference, in_band)

        self.time += DT
        return self.history.get()

    def set_reference(self, value):
        self.reference = value

    def set_load(self, value):
        self.load = value

    def reset_gains(self, kp, ki):
        self.pid.reset_gains(kp, ki)

    def reset(self):
        self.time = 0.0
        self.process.reset()
        self.pid.integral = 0.0
        self.history.reset()


class History:
    """Buffer rodante con los datos para graficar."""

    def __init__(self):
        self.keys = ['time', 'latency', 'error', 'u', 'pods',
                     'load', 'reference', 'in_band']
        self.data = {k: [] for k in self.keys}

    def log(self, *values):
        for key, val in zip(self.keys, values):
            self.data[key].append(val)
            if len(self.data[key]) > POINTS_OF_HISTORY:
                self.data[key].pop(0)

    def reset(self):
        for key in self.data:
            self.data[key].clear()

    def get(self):
        return self.data
