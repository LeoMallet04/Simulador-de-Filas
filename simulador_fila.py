"""
Simulador de Fila - Modelagem Orientada a Eventos
Implementa G/G/c/K com Método Congruente Linear (LCG)
"""

import sys
from dataclasses import dataclass, field
from typing import List, Optional
import heapq

# ─── Gerador de Números Pseudoaleatórios (LCG) ───────────────────────────────

class LCGRandom:
    """Gerador Congruente Linear: X_{n+1} = (a * X_n + c) % M"""
    def __init__(self, seed: int, a: int = 1664525, c: int = 1013904223, M: int = 2**32):
        self.previous = seed
        self.a = a
        self.c = c
        self.M = M
        self.count = 0

    def next_random(self) -> float:
        """Retorna número pseudoaleatório normalizado [0, 1)"""
        self.previous = (self.a * self.previous + self.c) % self.M
        self.count += 1
        return self.previous / self.M

    def rand_between(self, low: float, high: float) -> float:
        """Retorna número uniformemente distribuído entre [low, high]"""
        return low + self.next_random() * (high - low)


# ─── Estruturas de Dados ──────────────────────────────────────────────────────

ARRIVAL   = 0
DEPARTURE = 1

@dataclass(order=True)
class Event:
    time: float
    kind: int  # ARRIVAL or DEPARTURE
    server: int = field(default=0, compare=False)  # which server (for departure)

# ─── Simulador ────────────────────────────────────────────────────────────────

class QueueSimulator:
    def __init__(
        self,
        servers: int,       # c: número de servidores
        capacity: int,      # K: capacidade máxima da fila (inclui em serviço)
        arrival_min: float,
        arrival_max: float,
        service_min: float,
        service_max: float,
        max_randoms: int = 100_000,
        seed: int = 12345,
        first_arrival: float = 2.0,
    ):
        self.servers      = servers
        self.capacity     = capacity
        self.arrival_min  = arrival_min
        self.arrival_max  = arrival_max
        self.service_min  = service_min
        self.service_max  = service_max
        self.max_randoms  = max_randoms
        self.first_arrival = first_arrival

        self.rng = LCGRandom(seed)

        # Estado da fila
        self.queue_size   = 0         # número de clientes no sistema
        self.servers_busy = 0         # servidores ocupados
        self.global_time  = 0.0

        # Acumuladores de tempo por estado (índice = número de clientes no sistema)
        self.time_in_state = [0.0] * (capacity + 1)
        self.last_event_time = 0.0

        # Escalonador (min-heap por tempo)
        self.scheduler: List[Event] = []

        # Estatísticas
        self.losses   = 0
        self.arrivals = 0
        self.departures = 0

    def _schedule(self, event: Event):
        heapq.heappush(self.scheduler, event)

    def _next_event(self) -> Event:
        return heapq.heappop(self.scheduler)

    def _accumulate(self, current_time: float):
        """Acumula o tempo no estado atual antes de mudar de estado."""
        delta = current_time - self.last_event_time
        state = min(self.queue_size, self.capacity)
        self.time_in_state[state] += delta
        self.last_event_time = current_time

    def _rand_arrival(self) -> float:
        return self.rng.rand_between(self.arrival_min, self.arrival_max)

    def _rand_service(self) -> float:
        return self.rng.rand_between(self.service_min, self.service_max)

    def _handle_arrival(self, event: Event):
        self.arrivals += 1
        self._accumulate(event.time)
        self.global_time = event.time

        if self.queue_size < self.capacity:
            self.queue_size += 1
            if self.servers_busy < self.servers:
                # Inicia atendimento imediatamente
                self.servers_busy += 1
                service_time = self._rand_service()
                if self.rng.count < self.max_randoms:
                    self._schedule(Event(event.time + service_time, DEPARTURE))
        else:
            # Fila cheia → perda
            self.losses += 1

        # Agenda próxima chegada (se ainda houver aleatórios)
        if self.rng.count < self.max_randoms:
            interarrival = self._rand_arrival()
            self._schedule(Event(event.time + interarrival, ARRIVAL))

    def _handle_departure(self, event: Event):
        self.departures += 1
        self._accumulate(event.time)
        self.global_time = event.time

        self.queue_size   = max(0, self.queue_size - 1)

        if self.queue_size >= self.servers_busy:
            # Ainda há clientes esperando → inicia próximo atendimento
            if self.rng.count < self.max_randoms:
                service_time = self._rand_service()
                self._schedule(Event(event.time + service_time, DEPARTURE))
        else:
            self.servers_busy = max(0, self.servers_busy - 1)

    def run(self) -> dict:
        # Agenda primeira chegada
        self._schedule(Event(self.first_arrival, ARRIVAL))

        while self.scheduler and self.rng.count < self.max_randoms:
            event = self._next_event()
            if event.kind == ARRIVAL:
                self._handle_arrival(event)
            else:
                self._handle_departure(event)

        # Drena eventos restantes no escalonador (sem gerar novos aleatórios)
        while self.scheduler:
            event = self._next_event()
            self._accumulate(event.time)
            self.global_time = event.time
            if event.kind == DEPARTURE:
                self.departures += 1
                self.queue_size = max(0, self.queue_size - 1)
                if self.queue_size < self.servers_busy:
                    self.servers_busy = max(0, self.servers_busy - 1)

        # Acumula tempo final
        self._accumulate(self.global_time)

        total_time = self.global_time
        probabilities = [t / total_time if total_time > 0 else 0 for t in self.time_in_state]

        return {
            "config": f"G/G/{self.servers}/{self.capacity}",
            "arrivals": self.arrivals,
            "departures": self.departures,
            "losses": self.losses,
            "global_time": total_time,
            "randoms_used": self.rng.count,
            "time_in_state": self.time_in_state,
            "probabilities": probabilities,
            "capacity": self.capacity,
        }


def print_results(results: dict):
    config = results["config"]
    print(f"\n{'='*60}")
    print(f"  Simulação: {config}")
    print(f"{'='*60}")
    print(f"  Chegadas totais : {results['arrivals']}")
    print(f"  Saídas totais   : {results['departures']}")
    print(f"  Perdas          : {results['losses']}")
    print(f"  Aleatórios usados: {results['randoms_used']}")
    print(f"  Tempo global    : {results['global_time']:.4f}")
    print(f"\n  {'Estado':>8}  {'Tempo Acum.':>14}  {'Probabilidade':>14}")
    print(f"  {'-'*40}")
    for i in range(results['capacity'] + 1):
        t = results['time_in_state'][i]
        p = results['probabilities'][i]
        print(f"  {i:>8}  {t:>14.4f}  {p:>13.4f}%".replace("%", " (%)"))
        # reformat
    print()
    # reprint nicely
    print(f"\n  {'Estado':>8}  {'Tempo Acum.':>14}  {'Prob (%)':>10}")
    print(f"  {'-'*38}")
    for i in range(results['capacity'] + 1):
        t = results['time_in_state'][i]
        p = results['probabilities'][i] * 100
        print(f"  {i:>8}  {t:>14.4f}  {p:>9.4f}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # ── Simulação 1: G/G/1/5 ──────────────────────────────────────────────────
    sim1 = QueueSimulator(
        servers=1, capacity=5,
        arrival_min=2, arrival_max=5,
        service_min=3, service_max=5,
        max_randoms=100_000,
        seed=12345,
        first_arrival=2.0,
    )
    r1 = sim1.run()
    print_results(r1)

    # ── Simulação 2: G/G/2/5 ──────────────────────────────────────────────────
    sim2 = QueueSimulator(
        servers=2, capacity=5,
        arrival_min=2, arrival_max=5,
        service_min=3, service_max=5,
        max_randoms=100_000,
        seed=12345,
        first_arrival=2.0,
    )
    r2 = sim2.run()
    print_results(r2)
