from typing import List

from rich import box
from rich.align import Align
from rich.console import Group as RGroup
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from core.models import Paso
from ui.constants import CONCEPTO_COLOR, CONCEPTO_LABEL, ESTADO_COLOR, ESTADO_ICONO

class WPaso(Static):
    """Panel izquierdo: explicación del paso."""

class WCPU(Static):
    """Panel central arriba: estado del CPU."""

class WProcesos(Static):
    """Panel central abajo: colas de procesos."""

class WMemoria(Static):
    """Panel derecho: RAM + cache."""

class WProgreso(Static):
    """Barra de progreso inferior."""

class SimuladorApp(App):
    CSS = """
    Screen {
        background: #0d1117;
    }
    Header {
        background: #161b22;
        color: #c9d1d9;
    }
    Footer {
        background: #161b22;
        color: #8b949e;
    }

    #layout {
        height: 1fr;
    }

    /* Panel izquierdo */
    WPaso {
        width: 40%;
        border: round #30363d;
        padding: 0;
    }

    /* Panel central */
    #central {
        width: 28%;
        border: round #30363d;
    }
    WCPU {
        height: 55%;
        border-bottom: solid #30363d;
        padding: 0 1;
    }
    WProcesos {
        height: 1fr;
        padding: 0 1;
    }

    /* Panel derecho */
    WMemoria {
        width: 1fr;
        border: round #30363d;
        padding: 0 1;
    }

    /* Progreso */
    WProgreso {
        height: 3;
        background: #161b22;
        border-top: solid #30363d;
        padding: 0 2;
        content-align: left middle;
    }
    """

    BINDINGS = [
        ("space",  "siguiente",  "Siguiente / Pausar"),
        ("right",  "siguiente",  ""),
        ("left",   "anterior",   "Anterior"),
        ("a",      "auto",       "Auto"),
        ("plus",   "mas_rapido", "+Rapido"),
        ("minus",  "mas_lento",  "-Lento"),
        ("q",      "quit",       "Salir"),
    ]

    VELOCIDADES = [2.0, 1.0, 0.5, 0.25]
    VEL_LABELS  = ["Lenta 🐢", "Normal 🚶", "Rapida 🏃", "Turbo ⚡"]

    def __init__(self, pasos: List[Paso]):
        super().__init__()
        self.pasos    = pasos
        self.idx: int = 0
        self._auto    = False
        self._vel_idx = 1
        self._timer   = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="layout"):
            yield WPaso(id="w-paso")
            with Vertical(id="central"):
                yield WCPU(id="w-cpu")
                yield WProcesos(id="w-procs")
            yield WMemoria(id="w-mem")
        yield WProgreso(id="w-prog")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Simulador de Sistema Operativo"
        self._render()

    def action_siguiente(self) -> None:
        if self._auto:
            self._detener_auto()
            return
        if self.idx < len(self.pasos) - 1:
            self.idx += 1
            self._render()

    def action_anterior(self) -> None:
        if self._auto:
            self._detener_auto()
            return
        if self.idx > 0:
            self.idx -= 1
            self._render()

    def action_auto(self) -> None:
        if self._auto:
            self._detener_auto()
        else:
            self._iniciar_auto()

    def action_mas_rapido(self) -> None:
        if self._vel_idx < len(self.VELOCIDADES) - 1:
            self._vel_idx += 1
            if self._auto:
                self._detener_auto()
                self._iniciar_auto()
            self._render()

    def action_mas_lento(self) -> None:
        if self._vel_idx > 0:
            self._vel_idx -= 1
            if self._auto:
                self._detener_auto()
                self._iniciar_auto()
            self._render()

    def _iniciar_auto(self) -> None:
        self._auto  = True
        intervalo   = self.VELOCIDADES[self._vel_idx]
        self._timer = self.set_interval(intervalo, self._tick_auto)
        self._render()

    def _detener_auto(self) -> None:
        self._auto = False
        if self._timer:
            self._timer.stop()
            self._timer = None
        self._render()

    def _tick_auto(self) -> None:
        if self.idx < len(self.pasos) - 1:
            self.idx += 1
            self._render()
        else:
            self._detener_auto()

    def _render(self) -> None:
        p = self.pasos[self.idx]
        self.query_one("#w-paso",  WPaso).update(self._r_paso(p))
        self.query_one("#w-cpu",   WCPU).update(self._r_cpu(p))
        self.query_one("#w-procs", WProcesos).update(self._r_procs(p))
        self.query_one("#w-mem",   WMemoria).update(self._r_mem(p))
        self.query_one("#w-prog",  WProgreso).update(self._r_prog())

    def _r_paso(self, p: Paso) -> Panel:
        col = CONCEPTO_COLOR.get(p.concepto, "white")
        lbl = CONCEPTO_LABEL.get(p.concepto, p.concepto)

        t = Text()
        t.append(f"\n  {p.emoji}  ", style=f"bold {col}")
        t.append(f"{p.titulo}\n", style=f"bold {col}")
        t.append("\n")

        for linea in p.descripcion.split("\n"):
            t.append(f"  {linea}\n", style="white")

        t.append("\n")
        t.append("  📚 Concepto: ", style="dim")
        t.append(lbl, style=f"bold {col}")

        if p.instruccion_str:
            t.append("\n\n  💾 Instrucción: ", style="dim")
            t.append(p.instruccion_str, style="bold yellow")

        return Panel(
            t,
            title=f"[bold {col}] PASO {self.idx + 1} / {len(self.pasos)} [/]",
            border_style=col,
            padding=(0, 1),
        )

    def _r_cpu(self, p: Paso) -> Panel:
        if p.proceso_actual and p.proceso_actual in p.procesos:
            proc = p.procesos[p.proceso_actual]

            instr_lines: List[Text] = []
            for i, ins in enumerate(proc.instrucciones):
                t = Text()
                if i == proc.pc:
                    t.append(f" ► {ins}", style="bold yellow")
                elif i < proc.pc:
                    t.append(f"   {ins}", style="bright_black strike")
                else:
                    t.append(f"   {ins}", style="dim")
                instr_lines.append(t)

            tbl = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            tbl.add_column("k", style="dim", width=10)
            tbl.add_column("v", style="bold")

            tbl.add_row("Proceso",
                        f"[green]P{proc.pid} — {proc.nombre}[/green]")
            tbl.add_row("Estado",
                        f"[green]{ESTADO_ICONO.get(proc.estado,'')} {proc.estado}[/green]")
            tbl.add_row("PC",   f"[yellow]{proc.pc}[/yellow]")
            tbl.add_row("ACC",  f"[cyan]{proc.acc}[/cyan]")

            sep = Text("─" * 22, style="dim")
            lbl_ins = Text("  Instrucciones:", style="dim")

            return Panel(
                RGroup(tbl, sep, lbl_ins, *instr_lines),
                title="[bold green] 💻 CPU [/]",
                border_style="green",
            )
        else:
            return Panel(
                Align.center(
                    Text("\n  💤 CPU sin proceso\n      (ociosa)\n", style="dim"),
                    vertical="middle",
                ),
                title="[bold dim] 💻 CPU [/]",
                border_style="grey42",
            )

    def _r_procs(self, p: Paso) -> Panel:
        tbl = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        tbl.add_column("",   width=2)
        tbl.add_column("ID", width=3, style="bold")
        tbl.add_column("Estado", width=12)
        tbl.add_column("PC", width=3, justify="right")
        tbl.add_column("ACC", width=5, justify="right")

        for pid, proc in p.procesos.items():
            col = ESTADO_COLOR.get(proc.estado, "white")
            ico = ESTADO_ICONO.get(proc.estado, "")
            es_actual = pid == p.proceso_actual
            s = f"bold {col}" if es_actual else col
            cur = "►" if es_actual else " "
            tbl.add_row(
                f"[{s}]{cur}[/{s}]",
                f"[{s}]P{pid}[/{s}]",
                f"[{s}]{ico} {proc.estado}[/{s}]",
                f"[{s}]{proc.pc}[/{s}]",
                f"[{s}]{proc.acc}[/{s}]",
            )

        listos_s = " ".join(f"P{i}" for i in p.cola_listos) or "—"
        bloq_s   = " ".join(f"P{i}" for i in p.cola_bloqueados) or "—"
        term_s   = " ".join(f"P{i}" for i in p.terminados) or "—"

        return Panel(
            RGroup(
                tbl,
                Text(""),
                Text(f" 🟡 Listos : {listos_s}", style="yellow"),
                Text(f" 🔴 Bloq.  : {bloq_s}",  style="red"),
                Text(f" ⚫ Term.  : {term_s}",  style="bright_black"),
            ),
            title="[bold yellow] 📋 PROCESOS [/]",
            border_style="yellow",
        )

    def _r_mem(self, p: Paso) -> Panel:
        mem = p.memoria
        var = p.variable_accedida

        ram_tbl = Table(box=box.SIMPLE, show_header=True,
                        title="[bold blue]🔵 RAM[/bold blue]", padding=(0, 1))
        ram_tbl.add_column("Var",   width=5, style="bold")
        ram_tbl.add_column("Valor", width=6, justify="right")
        for k, v in mem.ram.items():
            if k == var:
                ram_tbl.add_row(f"[bold yellow]►{k}[/bold yellow]",
                                f"[bold yellow]{v}[/bold yellow]")
            else:
                ram_tbl.add_row(k, str(v))

        cap = mem.capacidad
        ocu = len(mem.cache)
        slots = "🟩" * ocu + "⬜" * (cap - ocu)

        cache_tbl = Table(box=box.SIMPLE, show_header=True,
                          title=f"[bold green]🟢 cache  {slots}[/bold green]",
                          padding=(0, 1))
        cache_tbl.add_column("Var",   width=5, style="bold")
        cache_tbl.add_column("Valor", width=6, justify="right")

        if mem.cache:
            for k, v in mem.cache.items():
                if k == var:
                    cache_tbl.add_row(f"[bold green]►{k}[/bold green]",
                                      f"[bold green]{v}[/bold green]")
                else:
                    cache_tbl.add_row(k, str(v))
        else:
            cache_tbl.add_row("[dim](vacía)[/dim]", "")

        leyenda = Text(
            f"\n  Velocidad:  cache ⚡⚡⚡  RAM ⚡",
            style="dim",
        )

        return Panel(
            RGroup(ram_tbl, Text(""), cache_tbl, leyenda),
            title="[bold magenta] 🧠 MEMORIA [/]",
            border_style="magenta",
        )

    def _r_prog(self) -> Text:
        total  = len(self.pasos)
        actual = self.idx + 1
        pct    = actual / total

        ancho  = 24
        llenos = int(ancho * pct)
        barra  = "█" * llenos + "░" * (ancho - llenos)

        t = Text()
        t.append(f" [{actual:>3}/{total}] ", style="bold white")
        t.append(f"|{barra}| ", style="cyan")
        t.append(f"{int(pct*100):>3}%  ", style="bold cyan")

        if self._auto:
            vel_lbl = self.VEL_LABELS[self._vel_idx]
            t.append(f" ▶ AUTO [{vel_lbl}]  ", style="bold green")
            t.append("ESPACIO Pausar   ", style="dim")
        else:
            t.append(" ⏸ MANUAL  ", style="bold yellow")
            t.append("ESPACIO/→ Avanzar   ", style="dim")

        t.append("A Auto/Pausa   + Mayor vel   - Menor vel   ← Retroceder   Q Salir",
                 style="dim")
        return t
