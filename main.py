from typing import Any
from QueueSimulator import QueueSimulator


def print_results(results: dict[str, Any]):
    config = results["config"]
    print(f"  Simulação: {config}")
    print(f"  Chegadas totais : {results['arrivals']}")
    print(f"  Saídas totais   : {results['departures']}")
    print(f"  Perdas          : {results['losses']}")
    print(f"  Aleatórios usados: {results['randoms_used']}")
    print(f"  Tempo global    : {results['global_time']:.4f}")
    print(f"\n  {'Estado':>8}  {'Tempo Acum.':>14}  {'Probabilidade':>14}")
    for i in range(results['capacity'] + 1):
        t = results['time_in_state'][i]
        p = results['probabilities'][i]
        print(f"  {i:>8}  {t:>14.4f}  {p:>13.4f}%".replace("%", " (%)"))


# G/G/1/5
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

# G/G/2/5
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