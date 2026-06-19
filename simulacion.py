"""
Simulación interactiva del lazo de control de latencia de un microservicio
mediante escalado automático de réplicas (modelo del HPA de Kubernetes).

Ejecutar:
    pip install -r requirements.txt
    python simulacion.py

Controles:
    - Sliders: Kp, Ki, Referencia (latencia objetivo) y Carga (perturbación).
    - Botones: Escalón de carga, Pausa/Reanudar, Reset, Cerrar.
    - Tecla Esc: cerrar.
"""

import tkinter.messagebox as messagebox

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import control as model

# --- Constantes de interfaz ---
SCAN_MS = 50                # cada cuánto refresca la pantalla (ms)
STEPS_PER_FRAME = 2         # pasos de simulación por refresco (acelera la vista)
VISIBLE_SECONDS = 45        # ventana temporal visible en los gráficos


class SliderConfig:
    def __init__(self, name, min, max, initial, fmt="{:.2f}"):
        self.name = name
        self.min = min
        self.max = max
        self.initial = initial
        self.fmt = fmt
        self.label = None
        self.widget = None


KP_CONFIG = SliderConfig("Kp", 0.0, 3.0, 0.4)
KI_CONFIG = SliderConfig("Ki", 0.0, 1.5, 0.15)
REF_CONFIG = SliderConfig("Referencia (ms)", 100.0, 400.0, 200.0, fmt="{:.0f}")
LOAD_CONFIG = SliderConfig("Carga (req/s)", 0.0, 60.0, 0.0, fmt="{:.0f}")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control de latencia por escalado de pods — Simulación")
        self.geometry("1280x820")
        self.minsize(1000, 650)
        self.bind("<Escape>", lambda e: self.on_closing())

        self.simulation = model.Simulation(
            KP_CONFIG.initial, KI_CONFIG.initial,
            REF_CONFIG.initial, LOAD_CONFIG.initial,
        )

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.controls_frame = ctk.CTkFrame(self, width=300)
        self.controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ns")

        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.plot_frame.grid_rowconfigure(0, weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)

        self.setup_controls()
        self.setup_plots()

        self.running = True
        self.paused = False
        self.after_id = self.after(SCAN_MS, self.update_loop)

    # ------------------------------------------------------------------ #
    #  Panel de controles
    # ------------------------------------------------------------------ #
    def setup_controls(self):
        title = ctk.CTkLabel(self.controls_frame, text="Parámetros del lazo",
                             font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(15, 5), padx=10)

        self.create_slider(KP_CONFIG, self.on_gain_change)
        self.create_slider(KI_CONFIG, self.on_gain_change)
        self.create_slider(REF_CONFIG, self.on_reference_change)
        self.create_slider(LOAD_CONFIG, self.on_load_change)

        step_btn = ctk.CTkButton(self.controls_frame,
                                 text="Escalón de carga (+20 req/s)",
                                 command=self.inject_load_step)
        step_btn.pack(pady=(15, 5), padx=10, fill="x")

        # Lectura en vivo
        self.readout = ctk.CTkLabel(self.controls_frame, text="",
                                    justify="left", font=ctk.CTkFont(size=13))
        self.readout.pack(pady=15, padx=10, anchor="w")

        # Botonera inferior
        bottom = ctk.CTkFrame(self.controls_frame)
        bottom.pack(side="bottom", pady=10, padx=10, fill="x")

        self.pause_button = ctk.CTkButton(bottom, text="Pausa",
                                          command=self.toggle_pause)
        self.pause_button.pack(side="left", expand=True, fill="x", padx=5, pady=8)

        close_button = ctk.CTkButton(bottom, text="Cerrar", command=self.on_closing)
        close_button.pack(side="left", expand=True, fill="x", padx=5, pady=8)

        reset_button = ctk.CTkButton(self.controls_frame, text="Reset",
                                     command=self.reset_simulation)
        reset_button.pack(side="bottom", pady=5, padx=10, fill="x")

    def create_slider(self, cfg, command):
        frame = ctk.CTkFrame(self.controls_frame)
        cfg.label = ctk.CTkLabel(
            frame, width=150,
            text=f"{cfg.name}: {cfg.fmt.format(cfg.initial)}")
        cfg.label.pack(side="top", anchor="w", padx=10, pady=(6, 0))

        def slider_command(value):
            cfg.label.configure(text=f"{cfg.name}: {cfg.fmt.format(value)}")
            command(value)

        cfg.widget = ctk.CTkSlider(frame, from_=cfg.min, to=cfg.max,
                                   command=slider_command)
        cfg.widget.set(cfg.initial)
        cfg.widget.pack(side="top", fill="x", padx=10, pady=(0, 8))
        frame.pack(pady=6, padx=10, fill="x")

    # ------------------------------------------------------------------ #
    #  Callbacks
    # ------------------------------------------------------------------ #
    def on_gain_change(self, _value):
        self.simulation.reset_gains(KP_CONFIG.widget.get(), KI_CONFIG.widget.get())

    def on_reference_change(self, value):
        self.simulation.set_reference(value)

    def on_load_change(self, value):
        self.simulation.set_load(value)

    def inject_load_step(self):
        new_load = min(LOAD_CONFIG.max, self.simulation.load + 20.0)
        self.simulation.set_load(new_load)
        LOAD_CONFIG.widget.set(new_load)
        LOAD_CONFIG.label.configure(
            text=f"{LOAD_CONFIG.name}: {LOAD_CONFIG.fmt.format(new_load)}")

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.configure(text="Reanudar" if self.paused else "Pausa")

    def reset_simulation(self):
        for cfg in (KP_CONFIG, KI_CONFIG, REF_CONFIG, LOAD_CONFIG):
            cfg.widget.set(cfg.initial)
            cfg.label.configure(text=f"{cfg.name}: {cfg.fmt.format(cfg.initial)}")
        self.simulation.reset_gains(KP_CONFIG.initial, KI_CONFIG.initial)
        self.simulation.set_reference(REF_CONFIG.initial)
        self.simulation.set_load(LOAD_CONFIG.initial)
        self.simulation.reset()

    # ------------------------------------------------------------------ #
    #  Gráficos
    # ------------------------------------------------------------------ #
    def setup_plots(self):
        plt.style.use("seaborn-v0_8-darkgrid")
        self.fig, self.axes = plt.subplots(
            4, 1, figsize=(9, 8), sharex=True,
            gridspec_kw={"height_ratios": [2, 1, 1.4, 1]})
        self.fig.subplots_adjust(hspace=0.35, left=0.12, right=0.97,
                                 top=0.96, bottom=0.08)

        ax_lat, ax_err, ax_pods, ax_load = self.axes

        self.line_lat = ax_lat.plot([], [], color="tab:blue", label="Latencia")[0]
        self.line_ref = ax_lat.plot([], [], color="tab:red", linestyle="--",
                                    label="Referencia")[0]
        ax_lat.set_ylabel("Latencia (ms)")
        ax_lat.set_ylim(80, 420)
        ax_lat.legend(loc="upper right", fontsize=9)
        self.band = None

        self.line_err = ax_err.plot([], [], color="tab:purple")[0]
        ax_err.axhline(0, color="gray", linewidth=0.8)
        ax_err.set_ylabel("Error (ms)")
        ax_err.set_ylim(-120, 120)

        self.line_pods = ax_pods.plot([], [], color="tab:green",
                                      drawstyle="steps-post")[0]
        ax_pods.set_ylabel("Réplicas (pods)")
        ax_pods.set_ylim(0, model.POD_MAX + 1)

        self.line_load = ax_load.plot([], [], color="tab:orange")[0]
        ax_load.set_ylabel("Carga (req/s)")
        ax_load.set_ylim(-2, LOAD_CONFIG.max + 5)
        ax_load.set_xlabel("Tiempo (s)")

        for ax in self.axes:
            ax.grid(True)
            ax.tick_params(labelsize=9)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=ctk.BOTH, expand=True)

    def update_plots(self, h):
        t = h["time"]
        self.line_lat.set_data(t, h["latency"])
        self.line_ref.set_data(t, h["reference"])
        self.line_err.set_data(t, h["error"])
        self.line_pods.set_data(t, h["pods"])
        self.line_load.set_data(t, h["load"])

        # Banda objetivo +/- alrededor de la referencia (se redibuja cada frame)
        if self.band is not None:
            self.band.remove()
        if t:
            ref = h["reference"]
            upper = [r + model.TARGET_BAND for r in ref]
            lower = [r - model.TARGET_BAND for r in ref]
            self.band = self.axes[0].fill_between(
                t, lower, upper, color="tab:red", alpha=0.12)

        if t:
            tmax = t[-1]
            tmin = max(0, tmax - VISIBLE_SECONDS)
            for ax in self.axes:
                ax.set_xlim(tmin, tmax if tmax > tmin else tmin + 1)

        self.canvas.draw_idle()

    def update_readout(self, h):
        if not h["time"]:
            return
        lat = h["latency"][-1]
        ref = h["reference"][-1]
        pods = h["pods"][-1]
        err = h["error"][-1]
        estado = "EN BANDA" if h["in_band"][-1] else "FUERA DE BANDA"
        self.readout.configure(
            text=(f"t = {h['time'][-1]:6.1f} s\n"
                  f"Latencia = {lat:6.1f} ms\n"
                  f"Referencia = {ref:6.0f} ms\n"
                  f"Error = {err:6.1f} ms\n"
                  f"Réplicas = {pods}\n"
                  f"Estado: {estado}"))

    # ------------------------------------------------------------------ #
    #  Bucle principal
    # ------------------------------------------------------------------ #
    def update_loop(self):
        if self.running and not self.paused:
            history = None
            for _ in range(STEPS_PER_FRAME):
                history = self.simulation.update()
            if history is not None:
                self.update_plots(history)
                self.update_readout(history)
        if self.running:
            self.after_id = self.after(SCAN_MS, self.update_loop)

    def on_closing(self):
        self.running = False
        try:
            save = messagebox.askyesno("Guardar gráfico",
                                       "¿Querés guardar una imagen del gráfico?")
            if save:
                self.fig.savefig("simulacion_latencia.png", dpi=150,
                                 bbox_inches="tight")
        except Exception:
            pass

        after_id = getattr(self, "after_id", None)
        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
