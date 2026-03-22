from collections import deque
from typing import Dict, List, Optional, Tuple

from core.models import Proceso, Memoria, Paso

class Simulacion:
    # Cerebro del Simulador que controla las ventanas de tiempo CPU y los estados de Procesos.
    def __init__(self, procesos_iniciales: List[Proceso] = None, memoria: Memoria = None, quantum: int = 2):
        self.pasos: List[Paso] = []
        self._n = 0
        self._procs: Dict[int, Proceso] = {}
        self._mem = memoria if memoria is not None else Memoria()
        self._listos: deque[Proceso] = deque()
        self._bloqueados: List[Proceso] = []
        self._terminados: List[int] = []
        self._ciclo = 0             # Ciclo global del sistema        
        self._quantum = quantum     # Cota de instrucciones permitida de forma continúa (Round Robin)
        self._ext_hecha = False     # Evita recrear la Interrupción de Prueba de forma infinita

        if procesos_iniciales:
            for p in procesos_iniciales:
                self._procs[p.pid] = p
                self._listos.append(p)

    def _snap(self) -> dict:
        # Saca la copia estricta de las colas para empaquetarlas en un Paso sin superposición de valor.
        self._n += 1
        return dict(
            numero=self._n,
            procesos={pid: p.copia() for pid, p in self._procs.items()},
            memoria=self._mem.copia(),
            cola_listos=[p.pid for p in self._listos],
            cola_bloqueados=[p.pid for p in self._bloqueados],
            terminados=list(self._terminados),
        )

    def _paso(self, titulo, descripcion, concepto, emoji,
              pid=None, var=None, instruccion=None):
        # Registra la captura de estado exacto en la historia (para posterior animación en la TUI).
        s = self._snap()
        self.pasos.append(Paso(
            titulo=titulo, descripcion=descripcion,
            concepto=concepto, emoji=emoji,
            proceso_actual=pid,
            variable_accedida=var,
            instruccion_str=instruccion,
            **s,
        ))

    def generar(self) -> List[Paso]:
        # Bucle madre de procesamiento. Emula el planificador a corto plazo del O.S. y Round-Robin.
        self._paso(
            "🖥️  INICIO DEL SISTEMA OPERATIVO",
            "¡Bienvenido al Simulador de SO!\n\n"
            f"Se cargan {len(self._procs)} PROCESOS en la cola de listos.\n\n"
            "📌 Un PROCESO es un programa en ejecución.\n"
            "📌 Todos esperan su turno para usar el CPU.",
            "inicio", "🖥️",
        )

        while self._listos or self._bloqueados:
            self._atender_bloqueados()

            # No tenemos listos pero sí bloqueados. Detenemos CPU a la espera:
            if not self._listos:
                self._paso(
                    "⏳  CPU OCIOSA — Esperando E/S",
                    "No hay procesos listos todavía.\n\n"
                    "La CPU espera a que los procesos bloqueados\n"
                    "terminen su operación de Entrada/Salida.",
                    "round_robin", "⏳",
                )
                self._ciclo += 1
                continue

            # Sacar el primer proceso (Planificador: Round Robin)
            proc = self._listos.popleft()
            proc.estado = "Ejecutando"
            prox_instr = proc.instrucciones[proc.pc] if proc.pc < len(proc.instrucciones) else "—"

            self._paso(
                f"▶️   P{proc.pid} ENTRA AL CPU",
                f"'{proc.nombre}' obtiene el CPU.\n\n"
                f"  Próxima instrucción: [{prox_instr}]\n\n"
                f"📌 QUANTUM = {self._quantum} instrucciones por turno.\n"
                f"📌 ROUND ROBIN: todos tienen un turno justo,\n"
                f"   nadie acapara el CPU para siempre.",
                "round_robin", "▶️", pid=proc.pid,
            )

            pasos_cpu = 0
            # Ciclo CPU de ejecución respetando el "Tiempo Restante del SO" permitido (Quantum)
            while pasos_cpu < self._quantum and proc.estado == "Ejecutando":

                # ── interrupción externa artificial simulada sólo en el ciclo #3 ─────────────
                if self._ciclo == 3 and not self._ext_hecha:
                    self._ext_hecha = True
                    self._paso(
                        "🔔  INTERRUPCIÓN EXTERNA",
                        "¡Llegó una señal del exterior!\n\n"
                        "Por ejemplo: alguien presionó una tecla.\n\n"
                        "📌 El SO detiene brevemente al proceso\n"
                        "   actual, atiende la señal y continúa.",
                        "interrupcion", "🔔", pid=proc.pid,
                    )

                instr = proc.instrucciones[proc.pc]

                # ── 1. FETCH: Buscamos qué hacer de la Memoria u Archivo de Instrucción ────────────────
                self._paso(
                    "📥  FETCH — Buscar instrucción en memoria",
                    f"El CPU busca la próxima instrucción.\n\n"
                    f"  PC = {proc.pc}  →  '{instr}'\n\n"
                    f"📌 El PC (Contador de Programa) siempre\n"
                    f"   apunta a la siguiente instrucción.",
                    "ciclo_instruccion", "📥",
                    pid=proc.pid, instruccion=instr,
                )

                partes = instr.split()
                op = partes[0]
                arg = partes[1] if len(partes) > 1 else None

                # ── 2. DECODE (Decodificación de Opcode) ────────────────
                self._paso(
                    f"🔍  DECODE — Decodificar '{instr}'",
                    f"El CPU analiza la instrucción:\n\n"
                    f"  Operación : [bold]{op}[/bold]\n"
                    f"  Argumento : {arg or '(ninguno)'}\n\n"
                    f"📌 La Unidad de Control interpreta\n"
                    f"   qué hay que hacer y con qué dato.",
                    "ciclo_instruccion", "🔍",
                    pid=proc.pid, instruccion=instr,
                )

                # ── 3. EXECUTE (Computación Real) ────────────────
                res = self._ejecutar(proc, op, arg)
                pasos_cpu += 1
                self._ciclo += 1
                self._atender_bloqueados()

                # Eventos posteriores a un proceso
                if res == "BLOQUEADO":
                    self._bloqueados.append(proc)
                    break
                if res == "TERMINADO":
                    break

            # ── interrupción de tiempo (El reloj/Tiro corto de RR) expulsa para dejar trabajar a otro ──
            if proc.estado == "Ejecutando":
                self._paso(
                    f"⏰  INTERRUPCIÓN DE RELOJ — P{proc.pid}",
                    f"¡El quantum de P{proc.pid} se agotó!\n\n"
                    f"Es como que un timer sonó.\n\n"
                    f"📌 P{proc.pid} vuelve AL FINAL de la cola\n"
                    f"   para que otros tengan su turno.",
                    "interrupcion", "⏰", pid=proc.pid,
                )
                proc.estado = "Listo"
                self._listos.append(proc)

        # Confirmamos sistema inactivo
        self._paso(
            "🏁  FIN DEL SISTEMA",
            "¡Todos los procesos terminaron!\n\n"
            "El sistema operativo completó su trabajo\n"
            "de forma exitosa.",
            "fin", "🏁",
        )
        return self.pasos

    def _atender_bloqueados(self):
        # Disminuye el temporizador E/S de bloqueados. Si acaba el tiempo, lo devuelve a listos.
        desbloqueados = []
        for p in self._bloqueados:
            p.espera_es -= 1
            if p.espera_es <= 0:
                desbloqueados.append(p)
        for p in desbloqueados:
            self._bloqueados.remove(p)
            p.estado = "Listo"
            self._listos.append(p)
            self._paso(
                f"✅  P{p.pid} TERMINA E/S — Vuelve a Listo",
                f"P{p.pid} terminó su operación de E/S.\n\n"
                f"Regresa a la cola de listos para\n"
                f"esperar su próximo turno en el CPU.",
                "interrupcion", "✅", pid=p.pid,
            )

    def _ejecutar(self, proc: Proceso, op: str, arg: Optional[str]) -> str:
        # Ejecuta una operación ALUM, lectura a Memoria, E/S o Finalización e impacta estado del thread. 
        if op == "CARGAR":
            valor, hit = self._leer(arg, proc.pid)
            proc.acc = valor
            proc.pc += 1
            self._paso(
                f"⚡  EXECUTE — CARGAR {arg}",
                f"Se carga el valor de '{arg}' en el acumulador.\n\n"
                f"  {arg} = {valor}  →  ACC = {valor}\n\n"
                f"📌 El acumulador (ACC) es el registro\n"
                f"   principal donde el CPU guarda\n"
                f"   el dato con el que está trabajando.",
                "ciclo_instruccion", "⚡",
                pid=proc.pid, var=arg, instruccion=f"CARGAR {arg}",
            )

        elif op == "SUMAR":
            prev = proc.acc
            valor, hit = self._leer(arg, proc.pid)
            proc.acc = prev + valor
            proc.pc += 1
            self._paso(
                f"⚡  EXECUTE — SUMAR {arg}",
                f"Se suma '{arg}' al acumulador.\n\n"
                f"  {prev} + {valor} = {proc.acc}\n"
                f"  ACC = {proc.acc}\n"
                f"  Fuente: {'🟢 cache (rápido!)' if hit else '🔵 RAM (lento)'}",
                "ciclo_instruccion", "⚡",
                pid=proc.pid, var=arg, instruccion=f"SUMAR {arg}",
            )

        elif op == "RESTAR":
            prev = proc.acc
            valor, hit = self._leer(arg, proc.pid)
            proc.acc = prev - valor
            proc.pc += 1
            self._paso(
                f"⚡  EXECUTE — RESTAR {arg}",
                f"Se resta '{arg}' del acumulador.\n\n"
                f"  {prev} - {valor} = {proc.acc}\n"
                f"  ACC = {proc.acc}\n"
                f"  Fuente: {'🟢 cache (rápido!)' if hit else '🔵 RAM (lento)'}",
                "ciclo_instruccion", "⚡",
                pid=proc.pid, var=arg, instruccion=f"RESTAR {arg}",
            )

        elif op == "GUARDAR":
            self._mem.ram[arg] = proc.acc
            self._mem.cache[arg] = proc.acc
            proc.pc += 1
            self._paso(
                f"⚡  EXECUTE — GUARDAR {arg}",
                f"Se guarda el acumulador en la variable '{arg}'.\n\n"
                f"  ACC ({proc.acc})  →  RAM[{arg}]\n"
                f"  ACC ({proc.acc})  →  cache[{arg}]",
                "memoria", "⚡",
                pid=proc.pid, var=arg, instruccion=f"GUARDAR {arg}",
            )

        elif op == "IMPRIMIR":
            valor, _ = self._leer(arg, proc.pid)
            proc.pc += 1
            self._paso(
                f"🖨️   EXECUTE — IMPRIMIR {arg} = {valor}",
                f"El proceso muestra el valor de '{arg}'.\n\n"
                f"  ► SALIDA: P{proc.pid}: {arg} = {valor}",
                "ciclo_instruccion", "🖨️",
                pid=proc.pid, var=arg, instruccion=f"IMPRIMIR {arg}",
            )

        elif op == "E/S":
            # Si necesita disco el SO suspende este hilo 2 tiempos por Entrada o Salida.
            proc.estado = "Bloqueado"
            proc.espera_es = 2
            proc.pc += 1
            self._paso(
                f"🔒  INTERRUPCIÓN E/S — P{proc.pid} se bloquea",
                f"P{proc.pid} necesita Entrada/Salida\n"
                f"(leer disco, red, etc.).\n\n"
                f"📌 En lugar de desperdiciar el CPU\n"
                f"   esperando, el SO suspende el proceso\n"
                f"   y ejecuta OTRO mientras tanto.",
                "interrupcion", "🔒",
                pid=proc.pid, instruccion="E/S",
            )
            return "BLOQUEADO"

        elif op == "FIN":
            # Libera el TCB y memoria de hilo.
            proc.estado = "Terminado"
            self._terminados.append(proc.pid)
            proc.pc += 1
            self._paso(
                f"🎉  P{proc.pid} TERMINÓ",
                f"¡'{proc.nombre}' completó todas sus\n"
                f"instrucciones!\n\n"
                f"El proceso se retira del sistema.",
                "fin_proceso", "🎉",
                pid=proc.pid, instruccion="FIN",
            )
            return "TERMINADO"

        return "CONTINUA"

    def _leer(self, var: str, pid: Optional[int] = None) -> Tuple[int, bool]:
        # Aplica la lógica real de jerarquía Cache L1 contra RAM local. Devuelve el número.
        
        # Primero siempre buscamos si existe en cache por un HIT asumiendo 0 demoras
        if var in self._mem.cache:
            valor_cache = self._mem.cache[var]
            self._paso(
                f"🟢  cache HIT — '{var}' encontrado",
                f"¡'{var}' ya está en la cache!\n\n"
                f"  Valor recuperado: {var} = {valor_cache}\n\n"
                f"📌 La cache es como el 'bolsillo' del CPU:\n"
                f"   pequeña, pero RAPIDÍSIMA.\n"
                f"   No hace falta ir a la RAM.",
                "memoria", "🟢", pid=pid, var=var,
            )
            return valor_cache, True

        # Sino buscamos la rama lenta de la RAM (Miss)
        valor = self._mem.ram[var]
        self._paso(
            f"🔵  cache MISS — '{var}' no está en cache",
            f"'{var}' no está en cache.\n\n"
            f"Hay que buscarlo en la RAM (más lenta).\n"
            f"Valor encontrado: {var} = {valor}",
            "memoria", "🔵", pid=pid, var=var,
        )

        # Si el tamaño en cache está saturado: borra mediante cola FIFO 
        if len(self._mem.cache) >= self._mem.capacidad:
            viejo = next(iter(self._mem.cache)) # Recupera el elemento más antiguo de la cache
            del self._mem.cache[viejo]
            self._paso(
                f"🔄  REEMPLAZO — '{viejo}' sale de cache",
                f"La cache está llena (máx {self._mem.capacidad}).\n\n"
                f"Se elimina '{viejo}' (el más antiguo)\n"
                f"para dar espacio a '{var}'.\n\n"
                f"📌 Política: FIFO (primero en entrar,\n"
                f"   primero en salir).",
                "memoria", "🔄", pid=pid, var=var,
            )

        # Almacena el valor fresco extraído de RAM en un espacio vacío de la cache
        self._mem.cache[var] = valor
        self._paso(
            f"📦  '{var}' cargado en cache",
            f"Se copia '{var}' de RAM a cache.\n\n"
            f"La próxima vez que se necesite '{var}'\n"
            f"será un cache HIT ⚡",
            "memoria", "📦", pid=pid, var=var,
        )
        return valor, False
