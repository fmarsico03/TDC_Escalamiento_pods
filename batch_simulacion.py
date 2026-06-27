import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import control as model


def run_simulation(kp, ki, lref, load_events, t_total):
    sim = model.Simulation(kp, ki, lref, load=0.0)
    steps = int(t_total / model.DT)
    for _ in range(steps):
        for t_event, load_value in load_events:
            if abs(sim.time - t_event) < model.DT / 2:
                sim.set_load(load_value)
        sim.update()
    return sim.history.get()


def print_metricas(data, label, lref):
    lat = data["latency"]
    n = len(lat)
    tail = lat[int(0.8 * n):]
    ess = sum(lref - v for v in tail) / len(tail)
    pico = max(lat) - lref
    print(f"\n  [{label}]")
    print(f"    Latencia máxima:          {max(lat):.1f} ms")
    print(f"    Error en estado estable:  {ess:.2f} ms")
    print(f"    Sobreimpulso sobre Lref:  {pico:.1f} ms")
    print(f"    Pods mín/máx:             {min(data['pods'])} / {max(data['pods'])}")


def main():
    # ── Configuración ─────────────────────────────────────────────
    KP       = 0.1
    KI       = 0.025
    LREF     = 200.0    # ms
    DURATION = 600.0    # s
    OUTPUT   = "simulacion_latencia.png"

    # Eventos de carga: (tiempo_s, carga_req_s)
    LOAD_EVENTS = [
        (0,  60),
    ]
    # ──────────────────────────────────────────────────────────────

    label = f"PI  Kp={KP}  Ki={KI}"

    print("=" * 58)
    print(f"  Lref         = {LREF:.0f} ms")
    print(f"  Duración     = {DURATION:.0f} s")
    print(f"  Perturbación = {[(int(t), v) for t, v in LOAD_EVENTS]}")
    print(f"  Escenario    : {label}")
    print("=" * 58)

    print("\nCorriendo simulación...")
    data = run_simulation(KP, KI, LREF, LOAD_EVENTS, DURATION)

    print("\nMétricas:")
    print_metricas(data, label, LREF)

    print("\nGenerando figura...")
    plt.style.use("seaborn-v0_8-darkgrid")
    fig = plt.figure(figsize=(12, 9))
    fig.suptitle(
        f"{label}  |  Lref={LREF:.0f} ms  |  "
        f"Perturbaciones: {[(int(t), int(v)) for t, v in LOAD_EVENTS]}",
        fontsize=10, y=0.98,
    )

    gspec = gridspec.GridSpec(4, 1, figure=fig,
                              height_ratios=[2, 1, 1.4, 1], hspace=0.45)
    ax_lat  = fig.add_subplot(gspec[0])
    ax_err  = fig.add_subplot(gspec[1], sharex=ax_lat)
    ax_pods = fig.add_subplot(gspec[2], sharex=ax_lat)
    ax_load = fig.add_subplot(gspec[3], sharex=ax_lat)

    t    = data["time"]
    band = model.TARGET_BAND

    ax_lat.plot(t, data["latency"], color="tab:blue", label=label)
    ax_lat.axhline(LREF, color="gray", linewidth=0.8, linestyle=":")
    ax_lat.fill_between(t,
                        [LREF - band] * len(t),
                        [LREF + band] * len(t),
                        color="tab:blue", alpha=0.08, label=f"Banda ±{band} ms")
    ax_lat.set_ylabel("Latencia (ms)")
    ax_lat.legend(loc="upper right", fontsize=8)
    ax_lat.set_title("Variable controlada", fontsize=9)
    for t_ev, _ in LOAD_EVENTS:
        ax_lat.axvline(t_ev, color="orange", linewidth=0.8, linestyle="--", alpha=0.6)

    ax_err.plot(t, data["error"], color="tab:blue")
    ax_err.axhline(0,     color="gray", linewidth=0.8)
    ax_err.axhline( band, color="gray", linewidth=0.5, linestyle=":")
    ax_err.axhline(-band, color="gray", linewidth=0.5, linestyle=":")
    ax_err.set_ylabel("Error (ms)")
    ax_err.set_title("Señal de error", fontsize=9)
    for t_ev, _ in LOAD_EVENTS:
        ax_err.axvline(t_ev, color="orange", linewidth=0.8, linestyle="--", alpha=0.6)

    ax_pods.step(t, data["pods"], color="tab:green", where="post")
    ax_pods.set_ylabel("Réplicas (pods)")
    ax_pods.set_ylim(1, model.POD_MAX + 1)
    ax_pods.set_yticks([1] + list(range(5, model.POD_MAX + 1, 5)))
    ax_pods.set_title("Acción de control (actuador)", fontsize=9)
    for t_ev, _ in LOAD_EVENTS:
        ax_pods.axvline(t_ev, color="orange", linewidth=0.8, linestyle="--", alpha=0.6)

    ax_load.step(t, data["load"], color="tab:orange", where="post")
    ax_load.set_ylabel("Carga (req/s)")
    ax_load.set_xlabel("Tiempo (s)")
    ax_load.set_title("Perturbación de carga", fontsize=9)
    for t_ev, _ in LOAD_EVENTS:
        ax_load.axvline(t_ev, color="orange", linewidth=0.8, linestyle="--", alpha=0.6)

    plt.savefig(OUTPUT, dpi=150, bbox_inches="tight")
    print(f"Figura guardada: {OUTPUT}")
    plt.show()


if __name__ == "__main__":
    main()
