from typing import Any, List
import heapq

from RandomGenerator import RandomGenerator
from Event import Event, ARRIVAL, DEPARTURE

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

        self.rng = RandomGenerator(seed)

        self.queue_size   = 0 # número de clientes no sistema
        self.servers_busy = 0 # servidores ocupados
        self.global_time  = 0.0

        # acumuladores de tempo por estado (índice = número de clientes)
        self.time_in_state = [0.0] * (capacity + 1)
        self.last_event_time = 0.0

        self.scheduler: List[Event] = [] # min-heap por tempo

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
                # atende cliente
                self.servers_busy += 1
                service_time = self._rand_service()
                if self.rng.count < self.max_randoms:
                    self._schedule(Event(event.time + service_time, DEPARTURE))
        else: # fila cheia
            self.losses += 1 # perde cliente

        # agenda próxima chegada se ainda houver aleatórios
        if self.rng.count < self.max_randoms:
            interarrival = self._rand_arrival()
            self._schedule(Event(event.time + interarrival, ARRIVAL))

    def _handle_departure(self, event: Event):
        self.departures += 1
        self._accumulate(event.time)
        self.global_time = event.time

        self.queue_size   = max(0, self.queue_size - 1)

        if self.queue_size >= self.servers_busy:
            # se ainda tem cliente esperando inicia próximo atendimento
            if self.rng.count < self.max_randoms:
                service_time = self._rand_service()
                self._schedule(Event(event.time + service_time, DEPARTURE))
        else:
            self.servers_busy = max(0, self.servers_busy - 1)

    def run(self) -> dict[str, Any]:
        # primeira chegada
        self._schedule(Event(self.first_arrival, ARRIVAL))

        while self.scheduler and self.rng.count < self.max_randoms:
            event = self._next_event()
            if event.kind == ARRIVAL:
                self._handle_arrival(event)
            else:
                self._handle_departure(event)

        # drena eventos restantes no escalonador (sem gerar novos aleatórios)
        while self.scheduler:
            event = self._next_event()
            self._accumulate(event.time)
            self.global_time = event.time
            if event.kind == DEPARTURE:
                self.departures += 1
                self.queue_size = max(0, self.queue_size - 1)
                if self.queue_size < self.servers_busy:
                    self.servers_busy = max(0, self.servers_busy - 1)

        # acumula tempo final
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