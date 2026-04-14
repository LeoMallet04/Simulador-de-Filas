from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import heapq

from RandomGenerator import RandomGenerator


ARRIVAL_EXTERNAL = 0
ARRIVAL_TRANSFER = 1
DEPARTURE = 2


@dataclass(order=True)
class NetworkEvent:
    time: float
    seq: int
    kind: int
    node_id: str
    stream_id: Optional[str] = None


@dataclass
class QueueNodeConfig:
    id: str
    servers: int
    capacity: int
    service_min: float
    service_max: float


@dataclass
class ExternalArrivalConfig:
    id: str
    target_node: str
    arrival_min: float
    arrival_max: float
    first_arrival: float = 0.0


class QueueNetworkSimulator:
    def __init__(
        self,
        nodes: list[QueueNodeConfig],
        routing: dict[str, list[tuple[Optional[str], float]]],
        external_arrivals: list[ExternalArrivalConfig],
        max_randoms: int = 100_000,
        seed: int = 12345,
    ):
        self.nodes = {node.id: node for node in nodes}
        self.routing = routing
        self.external_arrivals = {stream.id: stream for stream in external_arrivals}

        self.max_randoms = max_randoms
        self.rng = RandomGenerator(seed)

        # Estado por fila (node_id -> valor)
        self.queue_size = {node_id: 0 for node_id in self.nodes}
        self.servers_busy = {node_id: 0 for node_id in self.nodes}
        self.time_in_state = {
            node_id: [0.0] * (node.capacity + 1) for node_id, node in self.nodes.items()
        }
        self.last_state_change_time = {node_id: 0.0 for node_id in self.nodes}

        self.arrivals = {node_id: 0 for node_id in self.nodes}
        self.departures = {node_id: 0 for node_id in self.nodes}
        self.losses = {node_id: 0 for node_id in self.nodes}

        self.global_time = 0.0

        self.scheduler: list[NetworkEvent] = []
        self._seq_counter = 0

        self._validate_inputs()

    def _validate_inputs(self):
        for origin, table in self.routing.items():
            if origin not in self.nodes:
                raise ValueError(f"Roteamento contém origem inválida: {origin}")

            total_prob = 0.0
            for destination, prob in table:
                if destination is not None and destination not in self.nodes:
                    raise ValueError(
                        f"Roteamento contém destino inválido: {destination}"
                    )
                if prob < 0:
                    raise ValueError(
                        "Probabilidades de roteamento não podem ser negativas"
                    )
                total_prob += prob

            if total_prob > 1.0 + 1e-12:
                raise ValueError(
                    f"Soma das probabilidades de {origin} excede 1.0: {total_prob}"
                )

        for stream_id, stream in self.external_arrivals.items():
            if stream.target_node not in self.nodes:
                raise ValueError(
                    f"Chegada externa {stream_id} aponta para nó inexistente: {stream.target_node}"
                )

    def _schedule(
        self,
        time: float,
        kind: int,
        node_id: str,
        stream_id: Optional[str] = None,
    ):
        self._seq_counter += 1
        heapq.heappush(
            self.scheduler,
            NetworkEvent(time, self._seq_counter, kind, node_id, stream_id),
        )

    def _next_event(self) -> NetworkEvent:
        return heapq.heappop(self.scheduler)

    def _accumulate_node_until(self, node_id: str, current_time: float):
        delta = current_time - self.last_state_change_time[node_id]
        if delta < 0:
            raise RuntimeError("Tempo regressivo detectado na simulação")

        node = self.nodes[node_id]
        state = min(self.queue_size[node_id], node.capacity)
        self.time_in_state[node_id][state] += delta
        self.last_state_change_time[node_id] = current_time

    def _rand_arrival(self, stream_id: str) -> float:
        stream = self.external_arrivals[stream_id]
        return self.rng.rand_between(stream.arrival_min, stream.arrival_max)

    def _rand_service(self, node_id: str) -> float:
        node = self.nodes[node_id]
        return self.rng.rand_between(node.service_min, node.service_max)

    def _sample_routing_destination(self, origin: str) -> Optional[str]:
        if self.rng.count >= self.max_randoms:
            return None

        table = self.routing.get(origin, [])
        u = self.rng.next_random()

        cumulative = 0.0
        for destination, prob in table:
            cumulative += prob
            if u <= cumulative:
                return destination

        # Probabilidade residual sai do sistema.
        return None

    def _try_start_service(self, node_id: str, current_time: float):
        node = self.nodes[node_id]
        if (
            self.servers_busy[node_id] < node.servers
            and self.queue_size[node_id] > self.servers_busy[node_id]
        ):
            self.servers_busy[node_id] += 1
            if self.rng.count < self.max_randoms:
                service_time = self._rand_service(node_id)
                self._schedule(current_time + service_time, DEPARTURE, node_id)

    def _handle_arrival(self, event: NetworkEvent):
        node_id = event.node_id
        node = self.nodes[node_id]

        self.arrivals[node_id] += 1
        self._accumulate_node_until(node_id, event.time)
        self.global_time = event.time

        if self.queue_size[node_id] < node.capacity:
            self.queue_size[node_id] += 1
            self._try_start_service(node_id, event.time)
        else:
            self.losses[node_id] += 1

        if event.kind == ARRIVAL_EXTERNAL and event.stream_id is not None:
            if self.rng.count < self.max_randoms:
                interarrival = self._rand_arrival(event.stream_id)
                self._schedule(
                    event.time + interarrival,
                    ARRIVAL_EXTERNAL,
                    event.node_id,
                    stream_id=event.stream_id,
                )

    def _handle_departure(self, event: NetworkEvent):
        node_id = event.node_id

        self.departures[node_id] += 1
        self._accumulate_node_until(node_id, event.time)
        self.global_time = event.time

        self.queue_size[node_id] = max(0, self.queue_size[node_id] - 1)

        if self.queue_size[node_id] >= self.servers_busy[node_id]:
            if self.rng.count < self.max_randoms:
                service_time = self._rand_service(node_id)
                self._schedule(event.time + service_time, DEPARTURE, node_id)
        else:
            self.servers_busy[node_id] = max(0, self.servers_busy[node_id] - 1)

        destination = self._sample_routing_destination(node_id)
        if destination is not None:
            self._schedule(event.time, ARRIVAL_TRANSFER, destination)

    def _drain_without_randoms(self):
        while self.scheduler:
            event = self._next_event()
            self.global_time = event.time

            if event.kind == DEPARTURE:
                node_id = event.node_id
                self.departures[node_id] += 1
                self._accumulate_node_until(node_id, event.time)

                self.queue_size[node_id] = max(0, self.queue_size[node_id] - 1)
                if self.queue_size[node_id] < self.servers_busy[node_id]:
                    self.servers_busy[node_id] = max(0, self.servers_busy[node_id] - 1)
            else:
                # Sem novos aleatórios, chegadas pendentes são contabilizadas e descartadas.
                node_id = event.node_id
                self.arrivals[node_id] += 1
                self._accumulate_node_until(node_id, event.time)

    def run(self) -> dict[str, Any]:
        for stream_id, stream in self.external_arrivals.items():
            self._schedule(
                stream.first_arrival,
                ARRIVAL_EXTERNAL,
                stream.target_node,
                stream_id=stream_id,
            )

        while self.scheduler and self.rng.count < self.max_randoms:
            event = self._next_event()
            if event.kind in (ARRIVAL_EXTERNAL, ARRIVAL_TRANSFER):
                self._handle_arrival(event)
            else:
                self._handle_departure(event)

        self._drain_without_randoms()

        for node_id in self.nodes:
            self._accumulate_node_until(node_id, self.global_time)

        probabilities: dict[str, list[float]] = {}
        if self.global_time > 0:
            for node_id, times in self.time_in_state.items():
                probabilities[node_id] = [value / self.global_time for value in times]
        else:
            for node_id, times in self.time_in_state.items():
                probabilities[node_id] = [0.0 for _ in times]

        return {
            "config": {
                "nodes": {
                    node_id: {
                        "servers": node.servers,
                        "capacity": node.capacity,
                        "service": [node.service_min, node.service_max],
                    }
                    for node_id, node in self.nodes.items()
                },
                "external_arrivals": {
                    stream_id: {
                        "target": stream.target_node,
                        "arrival": [stream.arrival_min, stream.arrival_max],
                        "first_arrival": stream.first_arrival,
                    }
                    for stream_id, stream in self.external_arrivals.items()
                },
                "routing": self.routing,
            },
            "global_time": self.global_time,
            "randoms_used": self.rng.count,
            "nodes": {
                node_id: {
                    "arrivals": self.arrivals[node_id],
                    "departures": self.departures[node_id],
                    "losses": self.losses[node_id],
                    "time_in_state": self.time_in_state[node_id],
                    "probabilities": probabilities[node_id],
                    "capacity": self.nodes[node_id].capacity,
                }
                for node_id in self.nodes
            },
        }
