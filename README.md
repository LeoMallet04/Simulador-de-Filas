# Simulador-de-Filas

Simulador de filas orientado a eventos com suporte a rede de filas.

Nesta versão, o projeto já suporta:
- duas filas em tandem;
- topologia genérica com roteamento probabilístico entre filas.

## Pré-requisitos

- Python 3.10+ (recomendado 3.11+).

## Como executar

No diretório do projeto, rode:

```bash
python main.py
```

O programa imprime:
- configuração utilizada;
- total de aleatórios usados;
- tempo global da simulação;
- métricas por fila (chegadas, saídas, perdas, tempo por estado e probabilidade por estado).

## Como configurar a rede de filas

A configuração é feita no arquivo `main.py`, com três blocos:

1. `nodes`: definição de cada fila.
2. `external_arrivals`: fluxos de chegada externa.
3. `routing`: probabilidades de saída de uma fila para outra.

### 1) Definição das filas (`nodes`)

Cada fila usa `QueueNodeConfig`:

- `id`: identificador único da fila.
- `servers`: número de servidores da fila.
- `capacity`: capacidade máxima da fila (inclui clientes em serviço).
- `service_min` e `service_max`: intervalo de tempo de atendimento.

Exemplo:

```python
nodes = [
	QueueNodeConfig(id="Q1", servers=1, capacity=5, service_min=3, service_max=5),
	QueueNodeConfig(id="Q2", servers=2, capacity=5, service_min=2, service_max=4),
]
```

### 2) Chegadas externas (`external_arrivals`)

Cada fluxo externo usa `ExternalArrivalConfig`:

- `id`: identificador do fluxo.
- `target_node`: fila de entrada desse fluxo.
- `arrival_min` e `arrival_max`: intervalo entre chegadas.
- `first_arrival`: instante da primeira chegada.

Exemplo:

```python
external_arrivals = [
	ExternalArrivalConfig(
		id="A1",
		target_node="Q1",
		arrival_min=2,
		arrival_max=5,
		first_arrival=2.0,
	)
]
```

### 3) Roteamento (`routing`)

`routing` é um dicionário no formato:

```python
"ORIGEM": [("DESTINO", probabilidade), ("OUTRO_DESTINO", probabilidade), ...]
```

Regras:
- as probabilidades de cada origem devem somar no máximo `1.0`;
- `None` como destino significa saída do sistema;
- se a soma for menor que `1.0`, a probabilidade residual também representa saída do sistema.

Exemplo tandem (Q1 -> Q2 -> saída):

```python
routing = {
	"Q1": [("Q2", 1.0)],
	"Q2": [(None, 1.0)],
}
```

Exemplo com bifurcação:

```python
routing = {
	"Q1": [("Q2", 0.7), ("Q3", 0.2)],  # 10% residual sai do sistema
	"Q2": [(None, 1.0)],
	"Q3": [(None, 1.0)],
}
```

## Parâmetros gerais de execução

Ao criar `QueueNetworkSimulator`, você também pode configurar:

- `max_randoms`: limite de números aleatórios a serem usados na simulação;
- `seed`: semente do gerador pseudoaleatório.

Exemplo:

```python
sim = QueueNetworkSimulator(
	nodes=nodes,
	routing=routing,
	external_arrivals=external_arrivals,
	max_randoms=100_000,
	seed=12345,
)
```