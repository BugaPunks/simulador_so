import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class Proceso:
    # Representa un proceso listo para ejecutar dentro del SO
    pid: int
    nombre: str
    instrucciones: List[str]  # Conjunto de pasos del programa. Ej: ['CARGAR A', 'SUMAR B']
    pc: int = 0               # Program Counter: Guarda el índice de la línea que se debe ejecutar
    acc: int = 0              # Acumulador: Registro principal donde se operan las sumas/restas
    estado: str = "Listo"     # Los estados base: Listo, Ejecutando, Bloqueado o Terminado
    espera_es: int = 0        # Cuántos ciclos se demorará una tarea de Entrada/Salida si se bloquea

    def copia(self) -> "Proceso":
        return copy.deepcopy(self)


@dataclass
class Memoria:
    # Simula la memoria RAM estática y la memoria Cache rápida
    ram: Dict[str, int] = field(
        # Simula las celdas principales de un HDD o RAM Lenta
        default_factory=lambda: {"A": 10, "B": 5, "C": 0, "D": 8, "E": 2, "F": 0}
    )
    cache: Dict[str, int] = field(default_factory=dict) # Cache veloz en hardware política FIFO
    capacidad: int = 3  # Capacidad máxima permitida dentro de la cache simultáneamente

    def copia(self) -> "Memoria":
        return copy.deepcopy(self)


@dataclass
class Paso:
    # Toma una captura exacta del estado del sistema durante un solo momento de la simulación
    numero: int
    titulo: str
    descripcion: str
    concepto: str           # Clasifica el paso para pintar UI correcto de Textual
    emoji: str
    
    # Radiografía del sistema copiada en la instantánea
    procesos: Dict[int, Proceso]
    memoria: Memoria
    cola_listos: List[int]
    cola_bloqueados: List[int]
    terminados: List[int]
    proceso_actual: Optional[int]
    
    # Rastreadores del sistema visual
    variable_accedida: Optional[str] = None
    instruccion_str: Optional[str] = None
