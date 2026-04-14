from typing import Any

from QueueNetworkSimulator import (
    ExternalArrivalConfig,
    QueueNetworkSimulator,
    QueueNodeConfig,
)


def print_network_results(results: dict[str, Any]):
    print("  Simulação de rede de filas")
    print(f"  Configuração: {results['config']}")
    print(f"  Aleatórios usados: {results['randoms_used']}")
    print(f"  Tempo global: {results['global_time']:.4f}")

    for node_id, node_result in results["nodes"].items():
        print(f"\n  Fila: {node_id}")
        print(f"  Chegadas   : {node_result['arrivals']}")
        print(f"  Saídas     : {node_result['departures']}")
        print(f"  Perdas     : {node_result['losses']}")
        print(f"  {'Estado':>8}  {'Tempo Acum.':>14}  {'Probabilidade':>14}")

        for state in range(node_result["capacity"] + 1):
            t = node_result["time_in_state"][state]
            p = node_result["probabilities"][state]
            print(f"  {state:>8}  {t:>14.4f}  {100 * p:>13.4f} (%)")


# SINTAXE DE ENTRADA PROPOSTA:
# 1) nós (filas) com servidores, capacidade e intervalo de serviço
# 2) chegadas externas com intervalo de chegada e nó de destino
# 3) roteamento por probabilidades entre filas (None representa saída do sistema)
nodes = [
    QueueNodeConfig(id="Q1", servers=1, capacity=5, service_min=3, service_max=5),
    QueueNodeConfig(id="Q2", servers=2, capacity=5, service_min=2, service_max=4),
]

external_arrivals = [
    ExternalArrivalConfig(
        id="A1",
        target_node="Q1",
        arrival_min=2,
        arrival_max=5,
        first_arrival=2.0,
    )
]

routing = {
    "Q1": [("Q2", 1.0)],  # tandem: tudo que sai de Q1 entra em Q2
    "Q2": [(None, 1.0)],  # tudo que sai de Q2 deixa o sistema
}

sim = QueueNetworkSimulator(
    nodes=nodes,
    routing=routing,
    external_arrivals=external_arrivals,
    max_randoms=100_000,
    seed=12345,
)

simulation_results = sim.run()
print_network_results(simulation_results)
