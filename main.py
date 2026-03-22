from core.models import Proceso, Memoria
from core.simulador import Simulacion
from ui.app import SimuladorApp

def main():
    print("⏳ Generando pre-cómputo y cálculos del kernel O.S…")
    
    # definimos los procesos/tareas para el SO
    p1 = Proceso(1, "Proceso 1",
                 ["CARGAR A", "SUMAR B", "GUARDAR C", "IMPRIMIR C", "E/S", "FIN"])
    p2 = Proceso(2, "Proceso 2",
                 ["CARGAR D", "RESTAR E", "GUARDAR F", "IMPRIMIR F", "FIN"])
    p3 = Proceso(3, "Proceso 3",
                 ["CARGAR C", "SUMAR E", "IMPRIMIR C", "FIN"])

    procesos_lista = [p1, p2, p3]
    
    # definimos la capacidad limitante de cache
    memoria_inicial = Memoria(capacidad=3)
    
    # instanciamos las variables previamente definidas
    sim = Simulacion(procesos_iniciales=procesos_lista, memoria=memoria_inicial, quantum=2)
    
    # 🚀 4. INICIAR (Generando cache de pasos hacia listado interactivo)
    pasos = sim.generar()
    print(f"✅ {len(pasos)} pasos de máquina fueron generados localmente. Lanzando Interfaz interactiva…\n")
    
    # desplegamos la interfaz
    SimuladorApp(pasos).run()

if __name__ == "__main__":
    main()
