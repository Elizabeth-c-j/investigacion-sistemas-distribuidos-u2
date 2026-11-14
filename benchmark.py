#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Benchmark de relojes vectoriales vs. Lamport en topologias de malla.

Articulo:
    "Evaluacion Comparativa de Relojes Vectoriales vs. Lamport: Consumo de
    Memoria y Deteccion de Eventos Concurrentes en Topologias de Malla".

El script implementa un simulador de eventos discretos (cola de prioridad con
``heapq``) en el que ``N`` procesos generan 100 eventos cada uno (40 % locales,
60 % envios a un vecino aleatorio). Las recepciones se programan con un retardo
de red base de 10 ms mas un jitter uniforme en [0, 50] ms, lo que provoca
reordenamiento de mensajes.

Cada proceso mantiene simultaneamente un reloj de Lamport y un reloj
vectorial, y se evaluan ambas propuestas con las mismas trazas de eventos.

Verdad de referencia (ground truth)
-----------------------------------
La causalidad NO se deriva de ninguno de los relojes, sino del grafo de
causalidad construido de forma independiente:

* aristas de orden de programa (evento ``i`` -> evento ``i+1`` de un proceso),
* aristas de comunicacion (envio -> recepcion del mismo mensaje).

El *happens-before* se calcula por alcanzabilidad exacta sobre ese DAG usando
conjuntos de descendientes codificados como bitsets (enteros de Python). Como
todas las aristas apuntan hacia adelante en el orden global de ejecucion, ese
orden es un orden topologico valido y basta un recorrido inverso para obtener
los descendientes de cada evento en O(V + E) operaciones de bitset.

Definiciones de metricas (por reloj)
------------------------------------
* ``bytes_por_proceso`` / ``bytes_por_mensaje``: metadatos del reloj con
  8 bytes por entero (1 entero para Lamport, ``N`` para el vectorial).
* ``overhead_total_bytes``: suma de metadatos de todos los mensajes.
* ``memoria_tracemalloc_bytes``: pico medido con ``tracemalloc`` sobre una
  *reproduccion aislada* de la secuencia de operaciones de reloj, de modo que
  el pico atribuible sea exclusivamente el de las estructuras del reloj.
* ``pares_concurrentes_reales``: pares muestreados que son concurrentes segun
  la verdad de referencia.
* ``concurrentes_detectados``: pares concurrentes que el reloj declara
  incomparables. Un reloj escalar (Lamport) jamas declara incomparabilidad,
  por lo que su tasa de deteccion es 0.
* ``falsos_ordenamientos``: pares concurrentes que el reloj ordena como si
  fueran causales (Lamport: todos; vectorial: ninguno si es correcto).
* ``tasa_deteccion``: ``detectados / reales``.
* ``consistencia_causal``: porcentaje de pares causales ``a -> b`` en los que
  se cumple ``C(a) < C(b)`` (debe ser 100 % en ambos relojes).
* ``tiempo_ms``: tiempo de actualizacion de relojes medido con
  ``time.perf_counter_ns`` (solo la operacion del reloj, sin simulacion).

Uso
---
    python benchmark.py --rapido     # N = 4, 8, 16 y 5 repeticiones
    python benchmark.py              # N = 4, 8, 16, 32, 64 y 30 repeticiones

Genera ``results.csv`` y una tabla resumen (media +- desviacion estandar).
"""

from __future__ import annotations

import argparse
import csv
import heapq
import os
import random
import statistics
import sys
import time
import tracemalloc
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Parametros del diseno experimental
# ---------------------------------------------------------------------------

EVENTOS_POR_PROCESO: int = 100          # eventos propios generados por proceso
PROB_ENVIO: float = 0.6                 # 60 % envios, 40 % locales
RETARDO_BASE_MS: float = 10.0           # retardo de red base
JITTER_MAX_MS: float = 50.0             # jitter uniforme [0, 50] ms
DELTA_ENTRE_EVENTOS_MS: Tuple[float, float] = (0.5, 5.0)  # separacion de ops
BYTES_POR_ENTERO: int = 8               # tamano de un contador en metadatos
PARES_A_MUESTREAR: int = 20_000         # pares aleatorios por ejecucion
SEMILLA_BASE: int = 1000                # semilla = SEMILLA_BASE + repeticion
REPETICIONES: int = 30
N_COMPLETO: Tuple[int, ...] = (4, 8, 16, 32, 64)
N_RAPIDO: Tuple[int, ...] = (4, 8, 16)
REPETICIONES_RAPIDO: int = 5
K_VECINOS: int = 3                      # grado de la malla parcial
TOPOLOGIAS: Tuple[str, ...] = ("malla_completa", "malla_parcial")

#: Campos numericos que se agregaran en la tabla resumen final.
CAMPOS_NUMERICOS: Tuple[str, ...] = (
    "mensajes_totales",
    "bytes_por_proceso",
    "bytes_por_mensaje",
    "overhead_total_bytes",
    "memoria_tracemalloc_bytes",
    "pares_muestreados",
    "pares_concurrentes_reales",
    "concurrentes_detectados",
    "falsos_ordenamientos",
    "tasa_deteccion",
    "consistencia_causal",
    "tiempo_ms",
)


# ---------------------------------------------------------------------------
# Relojes logicos
# ---------------------------------------------------------------------------


class RelojLamport:
    """Reloj escalar de Lamport.

    Reglas formales implementadas:

    * evento local o envio: ``L = L + 1``
    * recepcion de mensaje con marca ``t``: ``L = max(L, t) + 1``
    """

    __slots__ = ("valor",)

    def __init__(self) -> None:
        self.valor: int = 0

    def incrementar(self) -> None:
        """Incrementa el contador en un evento local o en un envio."""
        self.valor += 1

    def recibir(self, marca_remota: int) -> None:
        """Actualiza el contador al recibir un mensaje con marca ``marca_remota``."""
        self.valor = max(self.valor, marca_remota) + 1


class RelojVectorial:
    """Reloj vectorial de ``n`` componentes (un contador por proceso).

    Reglas formales implementadas:

    * evento local o envio: ``V[pid] = V[pid] + 1``
    * recepcion de ``Vr``: ``V[i] = max(V[i], Vr[i])`` para todo ``i`` y
      despues ``V[pid] = V[pid] + 1``
    """

    __slots__ = ("n", "vector")

    def __init__(self, n: int) -> None:
        self.n: int = n
        self.vector: List[int] = [0] * n

    def incrementar(self, pid: int) -> None:
        """Incrementa la componente propia del proceso ``pid``."""
        self.vector[pid] += 1

    def recibir(self, remoto: Sequence[int], pid: int) -> None:
        """Fusiona el vector recibido componente a componente y luego incrementa."""
        local = self.vector
        for i in range(self.n):
            r = remoto[i]
            if r > local[i]:
                local[i] = r
        local[pid] += 1


def comparar_vectores(a: Sequence[int], b: Sequence[int]) -> int:
    """Compara dos marcas vectoriales.

    Devuelve ``-1`` si ``a < b`` (estrictamente, componente a componente),
    ``1`` si ``a > b`` y ``0`` si son incomparables (o iguales).
    """
    hay_menor = False
    hay_mayor = False
    for x, y in zip(a, b):
        if x < y:
            hay_menor = True
        elif x > y:
            hay_mayor = True
        if hay_menor and hay_mayor:
            return 0
    if hay_menor:
        return -1
    if hay_mayor:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Estructuras de simulacion
# ---------------------------------------------------------------------------


class Evento:
    """Evento ejecutado por un proceso, con sus dos marcas de tiempo.

    Atributos:
        pid: identificador del proceso que ejecuta el evento.
        lamport: marca escalar de Lamport del evento.
        vector: marca vectorial (tupla inmutable) del evento.
        envio_mid: identificador del mensaje si el evento es un envio.
        recibe_mid: identificador del mensaje si el evento es una recepcion.
    """

    __slots__ = ("pid", "lamport", "vector", "envio_mid", "recibe_mid")

    def __init__(
        self,
        pid: int,
        lamport: int,
        vector: Tuple[int, ...],
        envio_mid: Optional[int] = None,
        recibe_mid: Optional[int] = None,
    ) -> None:
        self.pid = pid
        self.lamport = lamport
        self.vector = vector
        self.envio_mid = envio_mid
        self.recibe_mid = recibe_mid


class Proceso:
    """Proceso simulado: programa de 100 operaciones y ambos relojes."""

    __slots__ = (
        "pid",
        "vecinos",
        "ops",
        "siguiente_op",
        "ultimo_evento",
        "reloj_lamport",
        "reloj_vector",
    )

    def __init__(
        self,
        pid: int,
        vecinos: Sequence[int],
        n: int,
        ops: Sequence[Tuple[int, int]],
    ) -> None:
        self.pid = pid
        self.vecinos = vecinos
        self.ops = ops
        self.siguiente_op = 0
        # Indice global del ultimo evento del proceso (orden de programa).
        self.ultimo_evento = -1
        self.reloj_lamport = RelojLamport()
        self.reloj_vector = RelojVectorial(n)


# ---------------------------------------------------------------------------
# Topologias
# ---------------------------------------------------------------------------


def _validar_topologia(vecinos: Sequence[Sequence[int]], n: int, grado: Optional[int]) -> None:
    """Comprueba simetria, ausencia de auto-lazos, grado y conectividad."""
    for i in range(n):
        v = list(vecinos[i])
        if len(set(v)) != len(v):
            raise ValueError(f"vecinos duplicados en el proceso {i}")
        if any(j == i or not (0 <= j < n) for j in v):
            raise ValueError(f"vecino invalido en el proceso {i}")
        if grado is not None and len(v) != grado:
            raise ValueError(f"el proceso {i} tiene grado {len(v)} != {grado}")
        for j in v:
            if i not in vecinos[j]:
                raise ValueError(f"arista asimetrica entre {i} y {j}")

    # Conectividad por BFS.
    visto = {0}
    pila = [0]
    while pila:
        u = pila.pop()
        for w in vecinos[u]:
            if w not in visto:
                visto.add(w)
                pila.append(w)
    if len(visto) != n:
        raise ValueError("la topologia no es conexa")


def _emparejamiento_sin_aristas_de_anillo(
    n: int, rng: random.Random, intentos: int = 500
) -> List[Tuple[int, int]]:
    """Emparejamiento perfecto aleatorio que evita las aristas del anillo."""
    for _ in range(intentos):
        orden = list(range(n))
        rng.shuffle(orden)
        pares: List[Tuple[int, int]] = []
        valido = True
        for i in range(n // 2):
            a, b = orden[i], orden[i + n // 2]
            if (a - b) % n in (1, n - 1):  # seria arista del anillo
                valido = False
                break
            pares.append((a, b))
        if valido:
            return pares
    # Respaldo determinista: nunca coincide con una arista del anillo si n >= 6.
    return [(i, i + n // 2) for i in range(n // 2)]


def construir_topologia(nombre: str, n: int, rng: random.Random) -> List[List[int]]:
    """Construye la lista de vecinos de cada proceso para la topologia dada.

    * ``malla_completa``: todos los procesos son vecinos de todos.
    * ``malla_parcial``: grafo conexo y regular de grado ``k = 3``. Se parte de
      un anillo (grado 2, conexo) y se anade un emparejamiento perfecto
      aleatorio que no repite aristas del anillo. Para ``n = 4`` el grado 3
      coincide con la malla completa, lo que se documenta como limitacion.
    """
    if nombre == "malla_completa":
        vecinos = [[j for j in range(n) if j != i] for i in range(n)]
        _validar_topologia(vecinos, n, grado=n - 1)
        return vecinos

    if nombre == "malla_parcial":
        if n % 2 != 0:
            raise ValueError("la malla parcial k=3 requiere n par")
        conjunto: List[set] = [set() for _ in range(n)]
        for i in range(n):  # anillo
            j = (i + 1) % n
            conjunto[i].add(j)
            conjunto[j].add(i)
        for a, b in _emparejamiento_sin_aristas_de_anillo(n, rng):
            conjunto[a].add(b)
            conjunto[b].add(a)
        vecinos = [sorted(s) for s in conjunto]
        _validar_topologia(vecinos, n, grado=min(K_VECINOS, n - 1))
        return vecinos

    raise ValueError(f"topologia desconocida: {nombre!r}")


# ---------------------------------------------------------------------------
# Verdad de referencia: alcanzabilidad en el grafo de causalidad
# ---------------------------------------------------------------------------


def calcular_descendientes(adyacencia: Sequence[Sequence[int]]) -> List[int]:
    """Conjuntos de descendientes (bitsets) del DAG de causalidad.

    El orden global de ejecucion es topologico porque toda arista (orden de
    programa o envio -> recepcion) apunta a un evento posterior. Recorriendo en
    orden inverso: ``desc[u] = {u} U union(desc[v] para v sucesor de u)``.
    """
    m = len(adyacencia)
    descendientes: List[int] = [0] * m
    for u in range(m - 1, -1, -1):
        acumulado = 1 << u
        for v in adyacencia[u]:
            acumulado |= descendientes[v]
        descendientes[u] = acumulado
    return descendientes


def muestrear_pares(m: int, rng: random.Random, k: int) -> List[Tuple[int, int]]:
    """Muestrea ``k`` pares de eventos distintos (sin reemplazo, ``a < b``)."""
    total = m * (m - 1) // 2
    k = min(k, total)
    if total <= 3 * k:  # poblacion pequena: muestreo directo uniforme
        todos = [(i, j) for i in range(m) for j in range(i + 1, m)]
        return rng.sample(todos, k)

    vistos: set = set()
    pares: List[Tuple[int, int]] = []
    while len(pares) < k:
        a = rng.randrange(m)
        b = rng.randrange(m)
        if a == b:
            continue
        if a > b:
            a, b = b, a
        clave = a * m + b
        if clave in vistos:
            continue
        vistos.add(clave)
        pares.append((a, b))
    return pares


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------


class MetricasReloj:
    """Resultado de un reloj para una ejecucion del simulador."""

    __slots__ = (
        "reloj",
        "bytes_por_proceso",
        "bytes_por_mensaje",
        "overhead_total_bytes",
        "memoria_tracemalloc_bytes",
        "pares_muestreados",
        "pares_concurrentes_reales",
        "concurrentes_detectados",
        "falsos_ordenamientos",
        "tasa_deteccion",
        "consistencia_causal",
        "tiempo_ms",
    )

    def __init__(self, reloj: str) -> None:
        self.reloj = reloj
        self.bytes_por_proceso = 0
        self.bytes_por_mensaje = 0
        self.overhead_total_bytes = 0
        self.memoria_tracemalloc_bytes = 0
        self.pares_muestreados = 0
        self.pares_concurrentes_reales = 0
        self.concurrentes_detectados = 0
        self.falsos_ordenamientos = 0
        self.tasa_deteccion = 0.0
        self.consistencia_causal = 0.0
        self.tiempo_ms = 0.0


# ---------------------------------------------------------------------------
# Simulador de eventos discretos
# ---------------------------------------------------------------------------


class Simulador:
    """Simulador de eventos discretos con cola de prioridad.

    Parameters
    ----------
    n:
        Numero de procesos.
    vecinos:
        Lista de adyacencia de la topologia.
    semilla:
        Semilla de la ejecucion; se derivan de ella los generadores de cada
        proceso (programa de eventos) y el generador de red (jitter y deltas).
    """

    def __init__(self, n: int, vecinos: Sequence[Sequence[int]], semilla: int) -> None:
        self.n = n
        self.vecinos = vecinos
        self.semilla = semilla

        # Generador independiente para la red: jitter y separacion de eventos.
        self.rng_red = random.Random(semilla * 104_729 + 7)

        self.procesos: List[Proceso] = [
            Proceso(pid, vecinos[pid], n, self._generar_ops(pid)) for pid in range(n)
        ]

        self.eventos: List[Evento] = []
        self.antes: List[int] = []           # evento previo del mismo proceso
        self.envio_idx: Dict[int, int] = {}  # mid -> indice global del envio
        self.recepcion_idx: Dict[int, int] = {}
        self.mensajes = 0
        self.tiempo_lamport_ns = 0
        self.tiempo_vector_ns = 0
        # Registro compacto de operaciones de reloj para el replay de memoria.
        self.log_reloj: List[Tuple[int, int, int, object]] = []

    # -- generacion del programa local -------------------------------------
    def _generar_ops(self, pid: int) -> List[Tuple[int, int]]:
        """Genera las 100 operaciones del proceso ``pid`` (0 = local, 1 = envio)."""
        rng = random.Random(self.semilla * 7919 + pid)
        candidatos = self.vecinos[pid]
        ops: List[Tuple[int, int]] = []
        for _ in range(EVENTOS_POR_PROCESO):
            if candidatos and rng.random() < PROB_ENVIO:
                ops.append((1, rng.choice(candidatos)))
            else:
                ops.append((0, -1))
        return ops

    # -- bucle principal ---------------------------------------------------
    def ejecutar(self) -> None:
        """Ejecuta la simulacion completa (bucle de eventos discretos)."""
        heap: List[tuple] = []
        contador = 0  # desempate estable en la cola de prioridad
        for pid in range(self.n):
            heapq.heappush(heap, (0.0, contador, 0, pid, -1, 0, ()))
            contador += 1

        while heap:
            tiempo, _, tipo, pid, mid, lam_recibido, vec_recibido = heapq.heappop(heap)
            proc = self.procesos[pid]
            idx = len(self.eventos)
            self.antes.append(proc.ultimo_evento)

            if tipo == 0:
                # --- evento propio: local o envio -------------------------
                clase, destino = proc.ops[proc.siguiente_op]
                proc.siguiente_op += 1

                t0 = time.perf_counter_ns()
                proc.reloj_lamport.incrementar()
                self.tiempo_lamport_ns += time.perf_counter_ns() - t0

                t0 = time.perf_counter_ns()
                proc.reloj_vector.incrementar(pid)
                self.tiempo_vector_ns += time.perf_counter_ns() - t0

                marca_l = proc.reloj_lamport.valor
                marca_v = tuple(proc.reloj_vector.vector)

                if clase == 0:  # evento local
                    self.eventos.append(Evento(pid, marca_l, marca_v))
                    self.log_reloj.append((0, pid, 0, ()))
                else:  # envio
                    self.mensajes += 1
                    mid_nuevo = self.mensajes
                    self.envio_idx[mid_nuevo] = idx
                    self.eventos.append(Evento(pid, marca_l, marca_v, envio_mid=mid_nuevo))
                    self.log_reloj.append((1, pid, 0, ()))
                    llegada = tiempo + RETARDO_BASE_MS + self.rng_red.uniform(0.0, JITTER_MAX_MS)
                    heapq.heappush(
                        heap,
                        (llegada, contador, 1, destino, mid_nuevo, marca_l, marca_v),
                    )
                    contador += 1

                proc.ultimo_evento = idx

                # Siguiente operacion propia del proceso (orden de programa).
                if proc.siguiente_op < len(proc.ops):
                    delta = self.rng_red.uniform(*DELTA_ENTRE_EVENTOS_MS)
                    heapq.heappush(heap, (tiempo + delta, contador, 0, pid, -1, 0, ()))
                    contador += 1

            else:
                # --- recepcion de un mensaje ------------------------------
                self.recepcion_idx[mid] = idx

                t0 = time.perf_counter_ns()
                proc.reloj_lamport.recibir(lam_recibido)
                self.tiempo_lamport_ns += time.perf_counter_ns() - t0

                t0 = time.perf_counter_ns()
                proc.reloj_vector.recibir(vec_recibido, pid)
                self.tiempo_vector_ns += time.perf_counter_ns() - t0

                self.eventos.append(
                    Evento(pid, proc.reloj_lamport.valor,
                           tuple(proc.reloj_vector.vector), recibe_mid=mid)
                )
                self.log_reloj.append((2, pid, lam_recibido, vec_recibido))
                proc.ultimo_evento = idx

    # -- grafo de causalidad ----------------------------------------------
    def construir_grafo(self) -> List[List[int]]:
        """Grafo de causalidad: orden de programa + envio -> recepcion."""
        m = len(self.eventos)
        adyacencia: List[List[int]] = [[] for _ in range(m)]
        for idx in range(m):
            previo = self.antes[idx]
            if previo >= 0:
                adyacencia[previo].append(idx)
        for mid, i_envio in self.envio_idx.items():
            adyacencia[i_envio].append(self.recepcion_idx[mid])
        return adyacencia

    # -- memoria de los relojes (medicion aislada) -------------------------
    def medir_memoria_reloj(self, reloj: str) -> int:
        """Pico de ``tracemalloc`` al reproducir solo las operaciones de reloj.

        La reproduccion se ejecuta fuera del simulador para que el pico medido
        corresponda unicamente a las estructuras del reloj (``N`` relojes).
        """
        tracemalloc.start()
        try:
            if reloj == "lamport":
                relojes: List = [RelojLamport() for _ in range(self.n)]
                for tipo, pid, lam, _ in self.log_reloj:
                    r = relojes[pid]
                    if tipo == 2:
                        r.recibir(lam)
                    else:
                        r.incrementar()
            else:
                relojes = [RelojVectorial(self.n) for _ in range(self.n)]
                for tipo, pid, _, vec in self.log_reloj:
                    r = relojes[pid]
                    if tipo == 2:
                        r.recibir(vec, pid)
                    else:
                        r.incrementar(pid)
            _, pico = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
            del relojes
        return int(pico)

    # -- evaluacion de un reloj sobre los pares muestreados ----------------
    def evaluar_reloj(
        self,
        reloj: str,
        pares: Sequence[Tuple[int, int]],
        real_causal: Sequence[bool],
    ) -> MetricasReloj:
        """Calcula las metricas de deteccion y consistencia para un reloj."""
        metricas = MetricasReloj(reloj)
        eventos = self.eventos
        ancho = 1 if reloj == "lamport" else self.n

        causales = 0
        correctos = 0
        concurrentes = 0
        detectados = 0
        falsos = 0

        if reloj == "lamport":
            for (a, b), es_causal in zip(pares, real_causal):
                la = eventos[a].lamport
                lb = eventos[b].lamport
                if es_causal:
                    causales += 1
                    if la < lb:  # a -> b implica estrictamente L(a) < L(b)
                        correctos += 1
                else:
                    # Un escalar siempre ordena: todo par concurrente es un
                    # falso ordenamiento y jamas se detecta concurrencia.
                    concurrentes += 1
                    falsos += 1
        else:
            for (a, b), es_causal in zip(pares, real_causal):
                va = eventos[a].vector
                vb = eventos[b].vector
                if es_causal:
                    causales += 1
                    if comparar_vectores(va, vb) == -1:
                        correctos += 1
                else:
                    concurrentes += 1
                    if comparar_vectores(va, vb) == 0:
                        detectados += 1
                    else:
                        falsos += 1

        metricas.pares_muestreados = len(pares)
        metricas.pares_concurrentes_reales = concurrentes
        metricas.concurrentes_detectados = detectados
        metricas.falsos_ordenamientos = falsos
        metricas.tasa_deteccion = (detectados / concurrentes) if concurrentes else 1.0
        metricas.consistencia_causal = (100.0 * correctos / causales) if causales else 100.0

        metricas.bytes_por_proceso = BYTES_POR_ENTERO * ancho
        metricas.bytes_por_mensaje = BYTES_POR_ENTERO * ancho
        metricas.overhead_total_bytes = metricas.bytes_por_mensaje * self.mensajes
        metricas.memoria_tracemalloc_bytes = self.medir_memoria_reloj(reloj)
        metricas.tiempo_ms = (
            self.tiempo_lamport_ns if reloj == "lamport" else self.tiempo_vector_ns
        ) / 1_000_000.0
        return metricas

    # -- ejecucion + medicion completa -------------------------------------
    def ejecutar_y_medir(self) -> Dict[str, MetricasReloj]:
        """Simula, construye la verdad de referencia y evalua ambos relojes."""
        self.ejecutar()
        adyacencia = self.construir_grafo()
        descendientes = calcular_descendientes(adyacencia)
        del adyacencia

        m = len(self.eventos)
        rng_pares = random.Random(self.semilla * 2_654_435_761 + 11)
        pares = muestrear_pares(m, rng_pares, PARES_A_MUESTREAR)

        # Verdad de referencia: a -> b sii b pertenece a los descendientes de a.
        real_causal = [bool(descendientes[a] & (1 << b)) for a, b in pares]
        del descendientes

        return {
            "lamport": self.evaluar_reloj("lamport", pares, real_causal),
            "vectorial": self.evaluar_reloj("vectorial", pares, real_causal),
        }


# ---------------------------------------------------------------------------
# Ejecucion del experimento y salida CSV
# ---------------------------------------------------------------------------


def columnas_csv() -> List[str]:
    """Cabecera exacta del fichero ``results.csv``."""
    return [
        "topologia",
        "n_procesos",
        "repeticion",
        "semilla",
        "reloj",
        "mensajes_totales",
        "bytes_por_proceso",
        "bytes_por_mensaje",
        "overhead_total_bytes",
        "memoria_tracemalloc_bytes",
        "pares_muestreados",
        "pares_concurrentes_reales",
        "concurrentes_detectados",
        "falsos_ordenamientos",
        "tasa_deteccion",
        "consistencia_causal",
        "tiempo_ms",
    ]


def ejecutar_experimento(
    n_valores: Sequence[int],
    repeticiones: int,
    ruta_salida: str,
) -> List[Dict[str, object]]:
    """Ejecuta todas las configuraciones y escribe los resultados en CSV."""
    filas: List[Dict[str, object]] = []
    total = len(TOPOLOGIAS) * len(n_valores) * repeticiones
    hecho = 0

    with open(ruta_salida, "w", newline="", encoding="utf-8") as fichero:
        escritor = csv.DictWriter(fichero, fieldnames=columnas_csv())
        escritor.writeheader()

        for topologia in TOPOLOGIAS:
            for n in n_valores:
                for repeticion in range(repeticiones):
                    semilla = SEMILLA_BASE + repeticion
                    rng_topologia = random.Random(semilla * 31 + n)
                    vecinos = construir_topologia(topologia, n, rng_topologia)

                    simulador = Simulador(n, vecinos, semilla)
                    metricas = simulador.ejecutar_y_medir()

                    for nombre_reloj in ("lamport", "vectorial"):
                        met = metricas[nombre_reloj]
                        fila: Dict[str, object] = {
                            "topologia": topologia,
                            "n_procesos": n,
                            "repeticion": repeticion,
                            "semilla": semilla,
                            "reloj": nombre_reloj,
                            "mensajes_totales": simulador.mensajes,
                            "bytes_por_proceso": met.bytes_por_proceso,
                            "bytes_por_mensaje": met.bytes_por_mensaje,
                            "overhead_total_bytes": met.overhead_total_bytes,
                            "memoria_tracemalloc_bytes": met.memoria_tracemalloc_bytes,
                            "pares_muestreados": met.pares_muestreados,
                            "pares_concurrentes_reales": met.pares_concurrentes_reales,
                            "concurrentes_detectados": met.concurrentes_detectados,
                            "falsos_ordenamientos": met.falsos_ordenamientos,
                            "tasa_deteccion": round(met.tasa_deteccion, 6),
                            "consistencia_causal": round(met.consistencia_causal, 4),
                            "tiempo_ms": round(met.tiempo_ms, 6),
                        }
                        escritor.writerow(fila)
                        filas.append(fila)

                    fichero.flush()
                    hecho += 1
                    print(
                        f"  [{hecho:>3}/{total}] {topologia:<15} N={n:<3} "
                        f"rep={repeticion + 1:<2} semilla={semilla} "
                        f"eventos={len(simulador.eventos)} msgs={simulador.mensajes}",
                        file=sys.stderr,
                    )
    return filas


# ---------------------------------------------------------------------------
# Tabla resumen
# ---------------------------------------------------------------------------

ANCHO_COLUMNA = 20


def _media_sd(valores: Sequence[float], factor: float, decimales: int) -> str:
    """Formatea ``media +- desviacion estandar`` escalada por ``factor``."""
    media = statistics.fmean(valores)
    sd = statistics.stdev(valores) if len(valores) > 1 else 0.0
    return f"{media / factor:.{decimales}f} +/- {sd / factor:.{decimales}f}"


def _agrupar(
    filas: Sequence[Dict[str, object]],
) -> Dict[Tuple[str, int, str], Dict[str, List[float]]]:
    """Agrupa las metricas por (topologia, N, reloj)."""
    grupos: Dict[Tuple[str, int, str], Dict[str, List[float]]] = {}
    for fila in filas:
        clave = (str(fila["topologia"]), int(fila["n_procesos"]), str(fila["reloj"]))
        grupo = grupos.setdefault(clave, {})
        for campo in CAMPOS_NUMERICOS:
            grupo.setdefault(campo, []).append(float(fila[campo]))
    return grupos


def _imprimir_tabla(
    titulo: str,
    claves: Sequence[Tuple[str, int, str]],
    grupos: Dict[Tuple[str, int, str], Dict[str, List[float]]],
    campos: Sequence[str],
    cabeceras: Sequence[str],
    factores: Sequence[float],
    decimales: Sequence[int],
) -> None:
    """Imprime una tabla de medias +- desviacion estandar."""
    print()
    print(titulo)
    print("-" * (15 + 5 + 11 + ANCHO_COLUMNA * len(campos)))
    cabecera = f"{'Topologia':<15}{'N':>4} {'Reloj':<10}"
    cabecera += "".join(f"{c:>{ANCHO_COLUMNA}}" for c in cabeceras)
    print(cabecera)
    print("-" * len(cabecera))

    topologia_anterior = None
    for clave in claves:
        topologia, n, reloj = clave
        if topologia != topologia_anterior:
            if topologia_anterior is not None:
                print("-" * len(cabecera))
            topologia_anterior = topologia
        linea = f"{topologia:<15}{n:>4} {reloj:<10}"
        grupo = grupos[clave]
        for campo, factor, dec in zip(campos, factores, decimales):
            linea += f"{_media_sd(grupo[campo], factor, dec):>{ANCHO_COLUMNA}}"
        print(linea)
    print("-" * len(cabecera))


def imprimir_resumen(filas: Sequence[Dict[str, object]], repeticiones: int) -> None:
    """Imprime el resumen agregado por topologia, N y reloj."""
    orden_reloj = {"lamport": 0, "vectorial": 1}
    grupos = _agrupar(filas)
    claves = sorted(
        grupos,
        key=lambda c: (c[0] != "malla_completa", c[1], orden_reloj.get(c[2], 9)),
    )

    print()
    print("=" * 150)
    print(f"RESUMEN EXPERIMENTAL (media +/- desviacion estandar, {repeticiones} repeticiones)")
    print("=" * 150)

    _imprimir_tabla(
        "A) DETECCION DE CONCURRENCIA Y CONSISTENCIA CAUSAL",
        claves,
        grupos,
        campos=(
            "pares_concurrentes_reales",
            "concurrentes_detectados",
            "falsos_ordenamientos",
            "tasa_deteccion",
            "consistencia_causal",
        ),
        cabeceras=(
            "Conc. reales",
            "Detectados",
            "Falsos orden.",
            "Tasa deteccion",
            "Consist. causal %",
        ),
        factores=(1.0, 1.0, 1.0, 1.0, 1.0),
        decimales=(0, 0, 0, 4, 2),
    )

    _imprimir_tabla(
        "B) RECURSOS Y TIEMPO DE ACTUALIZACION",
        claves,
        grupos,
        campos=(
            "mensajes_totales",
            "bytes_por_proceso",
            "bytes_por_mensaje",
            "overhead_total_bytes",
            "memoria_tracemalloc_bytes",
            "tiempo_ms",
        ),
        cabeceras=(
            "Mensajes",
            "Bytes/proceso",
            "Bytes/mensaje",
            "Overhead (MB)",
            "Mem. trace (KB)",
            "Tiempo (ms)",
        ),
        factores=(1.0, 1.0, 1.0, 1_000_000.0, 1024.0, 1.0),
        decimales=(0, 0, 0, 4, 2, 4),
    )


def verificar_resultados(filas: Sequence[Dict[str, object]]) -> bool:
    """Comprueba las invariantes teoricas esperadas del experimento."""
    ok = True
    print()
    print("VERIFICACION DE INVARIANTES")
    print("-" * 60)

    vectoriales = [f for f in filas if f["reloj"] == "vectorial"]
    lamports = [f for f in filas if f["reloj"] == "lamport"]

    malos_vec = [f for f in vectoriales if abs(float(f["tasa_deteccion"]) - 1.0) > 1e-9]
    print(
        f"[{'OK ' if not malos_vec else 'FALLO'}] vectorial: tasa_deteccion == 1.0 "
        f"({len(vectoriales) - len(malos_vec)}/{len(vectoriales)} filas)"
    )
    ok &= not malos_vec

    malos_cons = [
        f for f in filas
        if abs(float(f["consistencia_causal"]) - 100.0) > 1e-6
    ]
    print(
        f"[{'OK ' if not malos_cons else 'FALLO'}] consistencia_causal == 100 % en ambos "
        f"relojes ({len(filas) - len(malos_cons)}/{len(filas)} filas)"
    )
    ok &= not malos_cons

    malos_falsos = [f for f in vectoriales if int(f["falsos_ordenamientos"]) != 0]
    print(
        f"[{'OK ' if not malos_falsos else 'FALLO'}] vectorial: falsos_ordenamientos == 0 "
        f"({len(vectoriales) - len(malos_falsos)}/{len(vectoriales)} filas)"
    )
    ok &= not malos_falsos

    detecta_lamport = [f for f in lamports if int(f["concurrentes_detectados"]) != 0]
    print(
        f"[{'OK ' if not detecta_lamport else 'FALLO'}] lamport: concurrentes_detectados == 0 "
        f"({len(lamports) - len(detecta_lamport)}/{len(lamports)} filas)"
    )
    ok &= not detecta_lamport

    return ok


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Analiza argumentos, ejecuta el benchmark y muestra el resumen."""
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark de relojes vectoriales vs. Lamport en topologias de malla "
            "(memoria, deteccion de concurrencia y consistencia causal)."
        )
    )
    parser.add_argument(
        "--rapido",
        action="store_true",
        help="modo reducido: N = 4, 8, 16 y 5 repeticiones",
    )
    parser.add_argument(
        "--salida",
        default="results.csv",
        help="ruta del CSV de resultados (por defecto: results.csv)",
    )
    args = parser.parse_args(argv)

    n_valores = N_RAPIDO if args.rapido else N_COMPLETO
    repeticiones = REPETICIONES_RAPIDO if args.rapido else REPETICIONES
    ruta_salida = os.path.abspath(args.salida)

    print("Benchmark: relojes vectoriales vs. Lamport en topologias de malla")
    print(f"  N = {list(n_valores)}")
    print(f"  repeticiones = {repeticiones} (semilla = {SEMILLA_BASE} + repeticion)")
    print(f"  pares muestreados por ejecucion = {PARES_A_MUESTREAR}")
    print(f"  salida = {ruta_salida}")
    print()

    inicio = time.perf_counter()
    filas = ejecutar_experimento(n_valores, repeticiones, ruta_salida)
    transcurrido = time.perf_counter() - inicio

    imprimir_resumen(filas, repeticiones)
    verificar_resultados(filas)

    print()
    print(f"Resultados escritos en: {ruta_salida}")
    print(f"Filas: {len(filas)} | Tiempo total: {transcurrido:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
