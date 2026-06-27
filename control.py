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

ACCIÓN INVERSA:
    Más pods  =>  menos latencia.
    Así, cuando la carga sube, el lazo lleva u hacia valores negativos, lo
    que se traduce en MÁS pods.
"""

from utils import clamp

# --- Constantes ---

## Paso de integración
DT = 0.1                    # (s)  paso de tiempo virtual por ciclo

## Proceso (microservicio)
# tau = t_scrape + t_reconcile + t_coldstart = 15 + 15 + 30 = 60s
TAU = 60.0                  # (s)  constante de tiempo del proceso
L0 = 200.0                  # (ms) latencia base con pods nominales y sin carga extra
K = 10.0                    # (ms/pod) ganancia estática del proceso (acción inversa)
KD = 0.5                    # (ms·s/req) ganancia de la perturbación

## Actuador (Kubernetes)
POD_BASELINE = 4            # réplicas en el punto de operación (u = 0)
POD_MIN = 1                 # mínimo de réplicas
POD_MAX = 50                # máximo de réplicas (saturación del actuador)

## Banda objetivo / condición de falla
TARGET_BAND = 30.0          # (ms) tolerancia +/- alrededor de L_ref

## Historia (buffer de ploteo)
POINTS_OF_HISTORY = 2000


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
        # Al cambiar ganancias se limpia el estado para evitar transitorios bruscos.
        self.integral = 0.0


class MicroserviceModel:
    """Proceso de primer orden:  tau*dL/dt + L = L0 + K*u + Kd*d."""

    def __init__(self):
        self.latency = L0       # (ms) estado: latencia actual

    def update(self, u, load):
        # Euler hacia adelante (válido porque tau >> DT)
        dL = (L0 + K * u + KD * load - self.latency) / TAU
        self.latency += dL * DT
        return self.latency

    def reset(self):
        self.latency = L0


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
        # 1. Sensor ideal (H = 1): la realimentación es la latencia medida.
        feedback = self.process.latency
        error = self.reference - feedback          # e = L_ref - f  (realim. negativa)

        # 2. Controlador PI.
        u, p_term, i_term = self.pid.compute(error)

        # 3. Actuador (Ka = 1) + acción inversa: u -> cantidad de pods.
        pods = int(round(POD_BASELINE - u))
        pods = clamp(pods, POD_MIN, POD_MAX)
        u_eff = POD_BASELINE - pods                # acción efectivamente aplicada tras saturar

        # 4. Proceso: la planta responde a la acción efectiva y a la carga.
        latency = self.process.update(u_eff, self.load)

        # 5. Registro.
        in_band = abs(latency - self.reference) <= TARGET_BAND
        self.history.log(self.time, latency, error, u_eff, pods,
                         self.load, self.reference, in_band)

        self.time += DT
        return self.history.get()

    # --- Setters usados por la GUI ---
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
