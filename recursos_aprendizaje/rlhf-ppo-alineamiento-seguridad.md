# RLHF y PPO: cómo se entrena la alineación de seguridad de un LLM

> **Por qué este documento.** `safety-alignment-seguridad-agentica.md` explica
> **qué es** la alineación de seguridad y por qué es una pieza de seguridad
> —no solo de "buen comportamiento"— pero remite deliberadamente el mecanismo
> de entrenamiento a otro lado. `gradiente_finetuning_explicacion.md` ya
> cubre ese mecanismo a nivel general, como una de las tres técnicas modernas
> de fine-tuning: RLHF en tres etapas (preferencias → *reward model* → PPO).
> Este documento es el punto medio entre ambos: no repite el pipeline
> general, pero sí profundiza en **cómo se aplica específicamente cuando el
> objetivo es seguridad**, qué tensión introduce (*helpfulness* vs.
> *harmlessness*), qué tan universal es entre los laboratorios de frontera, y
> qué exige en infraestructura.
>
> **Qué asume ya sabido.** El ciclo de gradiente/backpropagation y el
> pipeline general de RLHF de 3 etapas (`gradiente_finetuning_explicacion.md`,
> Partes 1-2 y 4.3), y qué es la alineación de seguridad como propiedad —
> aprendida, no una regla dura verificada matemáticamente
> (`safety-alignment-seguridad-agentica.md`).
>
> **Qué no cubre.** La derivación completa del *policy gradient theorem* que
> sostiene a PPO, ni la estimación de *advantage* (GAE) que usa el crítico
> —esas sí se quedan en la intuición mecánica. La derivación de DPO, en
> cambio, se incluye completa: es corta, se sostiene con las mismas
> herramientas de la Parte 2 de `gradiente_finetuning_explicacion.md`, y
> explica *por qué* DPO puede prescindir del *reward model* y de PPO, no
> solo *que* puede.

## De "predecir texto plausible" a "rechazar con criterio"

Un modelo recién preentrenado no tiene ninguna noción de "peligroso". Si se
le pide un exploit o instrucciones para sintetizar un compuesto tóxico,
intenta completar el texto de la forma más verosímil posible según su
corpus de entrenamiento —exactamente el mismo mecanismo que usa para
completar cualquier otro texto, sin ningún concepto implícito de norma o
riesgo.

La alineación de seguridad no agrega una regla nueva al código del modelo
—no existe tal cosa como una regla dentro de una red neuronal—. Lo que hace
es **re-entrenar los pesos** para que el modelo *prefiera*, de forma
aprendida, generar rechazos seguros ante pedidos dañinos por sobre completar
esos pedidos, aunque técnicamente pudiera hacerlo. Esa preferencia se instala
en dos fases, apoyadas sobre el mismo pipeline de RLHF que ya conocés, pero
con un curado específico para seguridad:

- **La fase de SFT usa ejemplos de rechazo seguro.** Además de los pares
  (instrucción, respuesta ideal) para pedidos benignos, el dataset incluye
  pares donde el pedido es dañino y la respuesta ideal es un rechazo
  educado, directo y no evasivo —esto establece el comportamiento base antes
  de tocar RLHF.
- **El *reward model* se entrena con criterios de seguridad explícitos.**
  Los evaluadores (humanos, o un modelo evaluador en variantes como RLAIF)
  no solo comparan qué respuesta es "mejor" en general: juzgan
  específicamente *harmlessness* (¿el modelo se negó apropiadamente ante un
  pedido de riesgo?) junto con *helpfulness* (¿la respuesta sirve para algo
  ante un pedido legítimo?). Un dataset de *red teaming* —prompts
  adversariales diseñados para provocar fallas— alimenta buena parte de esa
  evaluación, específicamente para cubrir vectores como generación de
  malware, contenido CBRN, o sesgos severos.
- **PPO optimiza contra ese *reward model*, con la misma penalización KL**
  que ya viste —acá cumple un rol extra: evita que el modelo colapse hacia
  una única respuesta de rechazo genérica que maximiza el puntaje de
  seguridad sin aportar nada (un caso particular de *reward hacking*, el
  mismo fenómeno que se estudia como superficie de ataque en el Cap. 7 de
  este curso).

## El dilema central: *helpfulness* vs. *harmlessness*

El desafío técnico de fondo es que estas dos métricas tiran para lados
opuestos:

- **Helpfulness**: el modelo debe responder a la mayor cantidad posible de
  pedidos legítimos.
- **Harmlessness**: el modelo no debe generar contenido dañino, bajo ningún
  vector de ataque.

Si el término de recompensa por seguridad domina demasiado el entrenamiento,
el modelo cae en ***over-refusal***: rechaza pedidos benignos que comparten
vocabulario con temas sensibles. "¿Cómo funciona un virus informático a
nivel conceptual?" o "explicame la síntesis química del paracetamol" son
justo el tipo de pregunta legítima que un *reward model* mal calibrado
castiga por asociación superficial de palabras, no por intención real.

Vale la pena notar el paralelo con seguridad de software convencional: un
sistema que rechaza todo por las dudas no es "seguro", es **inútil por
sobre-restricción** —el equivalente, en alineamiento, de un firewall tan
agresivo que bloquea también el tráfico legítimo. La forma en que los
laboratorios atacan este problema es agregando datasets de *red teaming*
mixtos —pedidos benignos que rozan temas sensibles, junto a pedidos
genuinamente dañinos— para que el *reward model* aprenda a distinguir
intención, no solo vocabulario.

## ¿Se hace en todos los modelos de frontera?

Sí, pero no todos con la misma receta. Todos los laboratorios de frontera
usan alguna variante de alineamiento basado en preferencias, pero el método
concreto varió con el tiempo, sobre todo por costo de cómputo:

| Enfoque | Descripción | Ejemplos reportados |
|---|---|---|
| RLHF clásico (SFT + *reward model* + PPO) | El pipeline completo de tres etapas, con evaluadores humanos generando los datos de preferencia | El caso fundacional documentado es InstructGPT/GPT-3.5 de OpenAI; Llama 2 (Meta) también reporta esta receta, combinada con *rejection sampling* |
| RLAIF / Constitutional AI | Un modelo de IA, guiado por un conjunto explícito de principios ("constitución"), genera y evalúa las respuestas en vez de anotadores humanos en el bucle continuo | Es el nombre que usa específicamente Anthropic para el pipeline de Claude |
| DPO / IPO / KTO (familia de *preference optimization* directa) | Elimina el *reward model* separado y el ciclo explícito de RL; optimiza la política directamente sobre los pares de preferencia con una función de pérdida cerrada | Llama 3 (Meta) se apoya fuertemente en DPO combinado con *rejection sampling*; ampliamente adoptado también en modelos abiertos (Mistral, Qwen) por su menor costo de cómputo |

La tendencia general en los últimos años fue alejarse de PPO puro hacia DPO
y variantes —el próximo apartado explica por qué en términos de costo, y
más abajo por qué PPO, con todo, sigue siendo relevante para entender el
resto de la familia.

## PPO en términos intuitivos

**PPO (*Proximal Policy Optimization*)** es el algoritmo de aprendizaje por
refuerzo que ajusta los pesos del modelo durante RLHF clásico. Si el *reward
model* es el profesor que pone la nota, PPO es el método de estudio que usa
el modelo para mejorar esa nota sin volverse loco en el intento.

Pensalo como entrenar a un perro con premios. Si el perro hace bien un
truco, recibe una golosina y tiende a repetir esa acción. Pero corregir de
golpe, con pasos grandes, trae dos problemas:

- **Aprender demasiado rápido puede romper el modelo.** Si encuentra una
  respuesta que saca un puntaje altísimo —por ejemplo, contestar siempre
  "no puedo ayudarte con eso" porque así evita cualquier riesgo—, una
  actualización agresiva de pesos puede empujarlo de golpe hacia esa
  estrategia, perdiendo fluidez y capacidad de razonar en el proceso (el
  equivalente, en una red neuronal, del *catastrophic forgetting*).
- ***Reward hacking*.** Los modelos son buenos encontrando grietas en el
  sistema de evaluación para sumar puntaje sin cumplir el objetivo real —el
  mismo fenómeno que ya se mencionó arriba y que reaparece en el Cap. 7.

El adjetivo *proximal* (cercano) resume la solución: "buscá respuestas que
aumenten tu recompensa, pero no te alejes demasiado de cómo respondías hace
un instante — pasos chicos y controlados". Tres mecanismos concretos
implementan esa idea:

1. **El límite en la actualización (*clipped surrogate objective*).** PPO
   calcula cuánto mejora una respuesta nueva respecto de la anterior. Si esa
   mejora es descomunal —la probabilidad de una respuesta sube, por decir
   algo, un 500%—, el algoritmo **recorta** el gradiente en vez de aplicarlo
   completo. No importa cuán buena haya sido la recompensa: la actualización
   queda topada por una banda de tolerancia (típicamente 10-20%).
2. **El freno lingüístico (penalización KL).** PPO compara la respuesta del
   modelo actual contra el modelo de referencia —el mismo modelo, tal como
   quedó después de SFT, antes de tocar RLHF—. Si la distribución de
   palabras se aleja demasiado de ese punto de partida, se aplica una multa
   al puntaje. Esto mantiene coherencia sintáctica y evita que el modelo
   "descubra" un estilo de respuesta que maximiza el *reward model* pero ya
   no se lee como lenguaje natural.
3. **El crítico (*value function*).** Una segunda red, entrenada en
   paralelo, estima —token por token, no solo al final de la respuesta—
   cuánta recompensa espera acumular el modelo desde ese punto en adelante.
   Esto le permite al algoritmo atribuir qué palabra o frase específica hizo
   que la respuesta completa fuera buena o mala, en vez de juzgarla entera
   y a ciegas.

### El loop completo, paso a paso

Vale la pena fijar los roles con precisión, porque es fácil mezclarlos: **el
*reward model* es la función de pérdida externa** —un evaluador que toma una
respuesta y devuelve un número—, y **PPO es el optimizador** —el algoritmo
que toma ese número y decide cómo mover los pesos del LLM. Uno mide, el otro
actúa. En cada paso del entrenamiento:

```
[Prompt x] ──► [LLM, "Actor"] ──► [Respuesta y]
                                        │
                                        ▼
                                [Reward Model]
                                        │
                                        ▼
                              Score escalar (R)
                                        │
                                        ▼
                        [Algoritmo de RL: PPO]
                                        │
                                        ▼
                    Actualización de pesos Δθ del LLM
```

1. **Forward pass**: el LLM recibe el prompt `x` y genera la respuesta `y`,
   token por token, según su distribución de probabilidad actual.
2. **Reward scoring**: el par `(x, y)` pasa por el *reward model*, que emite
   el score `R`.
3. **Advantage y KL**: PPO toma ese score, le resta la penalización por
   alejarse del modelo de referencia (la divergencia KL ya vista), y usa el
   crítico para calcular el *advantage* —cuánto mejor fue esta respuesta
   respecto de lo que el crítico esperaba, no el score crudo.
4. **Backward pass**: PPO aplica el *clipped objective* sobre ese *advantage*
   y actualiza los pesos, haciendo más (o menos) probables los tokens de esa
   respuesta en el futuro.

Cuando se dice "alineamos el modelo con RLHF", el motor que ejecuta el
aprendizaje por refuerzo propiamente dicho es PPO —el *reward model* es la
guía que le indica hacia dónde ir, no el mecanismo que mueve los pesos.

**Por qué la tendencia se movió hacia DPO**: PPO es estable y efectivo, pero
caro — necesita mantener **cuatro modelos simultáneos en memoria** durante
el entrenamiento (el que aprende, el de referencia, el *reward model* y el
crítico). DPO logra un efecto equivalente de "no alejarse demasiado" +
"maximizar preferencia", pero reformulando el problema como una única
función de pérdida cerrada que se optimiza con descenso de gradiente
estándar —sin *reward model* separado, sin crítico, sin ciclo de RL
explícito. Es una simplificación real de ingeniería, no solo una elección de
gusto.

## DPO en profundidad: cómo elimina al Reward Model y a PPO

La idea intuitiva de DPO (*Direct Preference Optimization*, Rafailov et al.,
2023) ya apareció arriba: reformular el problema como una única función de
pérdida cerrada. Lo que todavía no se explicó es **por qué** eso es posible
—y la respuesta es una observación matemática elegante, no un truco de
ingeniería: **el propio LLM ya contiene, implícitamente, su mejor *reward
model* posible.** DPO no elimina el *reward model* por las buenas: demuestra
que nunca hizo falta entrenarlo por separado.

### La derivación, paso a paso

**Paso A — el objetivo de partida.** RLHF clásico busca la política `π_θ`
(los pesos del LLM) que maximiza la recompensa esperada del *reward model*
`r(x,y)`, penalizada por cuánto se aleja del modelo de referencia `π_ref`
—el mismo objetivo que ya se describió en palabras más arriba, ahora en
notación:

```
max_θ  E[r(x,y)] − β · D_KL(π_θ(y|x) || π_ref(y|x))
```

`β` es el coeficiente que regula esa distancia —el mismo "freno lingüístico"
de la sección anterior, ahora con nombre en la fórmula.

**Paso B — la solución tiene forma cerrada.** Resolver ese objetivo (con
multiplicadores de Lagrange) da una política óptima `π*` con esta forma
exacta:

```
π*(y|x) = (1/Z(x)) · π_ref(y|x) · exp((1/β) · r(x,y))
```

donde `Z(x)` es un normalizador (la "función de partición"). Despejando
`r(x,y)` de esa misma ecuación, se obtiene la **recompensa implícita**: la
diferencia de log-probabilidad entre el modelo ajustado y el de referencia,
escalada por `β`:

```
r(x,y) = β · log( π_θ(y|x) / π_ref(y|x) ) + β · log Z(x)
```

La intuición detrás de esta ecuación es el punto central de todo el
argumento: **la "recompensa" de una respuesta no es más que cuánto más (o
menos) probable la hace el modelo ajustado, comparado con el modelo base.**
No hace falta un evaluador externo para medir eso —ya está adentro de las
dos políticas.

**Paso C — sustituir en el modelo de preferencia.** El modelo estándar de
preferencia humana (Bradley-Terry) dice que la probabilidad de que una
respuesta preferida `y_w` (*winner*) le gane a una rechazada `y_l`
(*loser*) es una sigmoide de la diferencia de recompensas:

```
P(y_w ≻ y_l | x) = σ( r(x,y_w) − r(x,y_l) )
```

Sustituyendo la recompensa implícita del Paso B en esta ecuación, el término
`log Z(x)` **se cancela algebraicamente** —porque `Z(x)` depende solo del
prompt `x`, no de qué respuesta se compare, y aparece una vez con signo
positivo y otra con signo negativo. Lo que queda, sin ningún normalizador
pendiente, es la función de pérdida de DPO:

```
L_DPO(θ) = −E[ log σ( β·log(π_θ(y_w|x)/π_ref(y_w|x))
                     − β·log(π_θ(y_l|x)/π_ref(y_l|x)) ) ]
```

Esa cancelación es la jugada completa: empezó como un problema de RL con un
*reward model* externo, y terminó siendo una pérdida que se calcula
únicamente con las probabilidades que el propio LLM (y su copia de
referencia) ya asignan a las dos respuestas del par.

### Qué significa esto en la práctica

Con esta pérdida, entrenar por preferencias deja de ser un problema de
*reinforcement learning* y pasa a ser, mecánicamente, un problema de
clasificación sobre pares —el mismo descenso de gradiente y backpropagation
de siempre, sin generar nada nuevo durante el entrenamiento:

- **Sube la probabilidad de `y_w`** (penaliza si la respuesta preferida
  pierde probabilidad respecto al modelo de referencia).
- **Baja la probabilidad de `y_l`** (penaliza si la respuesta rechazada
  —la peligrosa, en el caso de seguridad— gana probabilidad).
- **El gradiente se autopondera por el error.** Si el modelo ya prefería
  correctamente `y_w` sobre `y_l`, el ajuste es chico. Si el modelo venía
  equivocado —le asignaba más probabilidad a la respuesta peligrosa—, el
  gradiente de corrección es máximo. Esto sale solo de la forma de la
  sigmoide, sin que nadie lo programe explícitamente.

### Limitaciones de DPO en alineamiento de seguridad

DPO no desplazó a PPO por completo en seguridad de frontera, por dos
límites reales:

- **No explora online.** DPO entrena sobre un dataset *estático* de pares ya
  etiquetados. Si un ataque nuevo cae fuera de la distribución de ese
  dataset, DPO no tiene forma de descubrirlo durante el entrenamiento —solo
  aprende de los pares que ya tiene. PPO, al generar respuestas nuevas en
  cada paso del loop de RL, sí explora activamente el espacio de respuestas
  posibles.
- **Es sensible a `β` y a pares ambiguos.** Un `β` mal calibrado, o un
  dataset con pares de preferencia poco claros, puede degradar la
  diversidad de respuestas del modelo o producir *over-refusal* severo —la
  misma falla de la sección anterior, ahora con una causa técnica concreta:
  la pérdida de DPO no tiene ningún mecanismo propio que distinga "esto es
  ambiguo" de "esto es claramente peor".

Por eso las implementaciones más recientes (Llama 3 es el caso documentado
más arriba) no usan DPO puro sobre un dataset fijo: usan variantes
**Iterative / Online DPO**, donde se generan respuestas nuevas con la
política actual en cada ronda, un *reward model* (o un evaluador) las
etiqueta como `y_w`/`y_l`, y recién con esos pares frescos se corre otra
epoch de DPO. Es, en los hechos, reintroducir una forma de exploración y de
evaluación externa —lo que PPO ya hacía— pero por fuera del loop de RL,
manteniendo la pérdida simple y barata de DPO en el paso de optimización
propiamente dicho.

## La infraestructura detrás del pipeline

A nivel de ingeniería, un pipeline de RLHF para seguridad tiene tres bloques
que se alimentan en cadena:

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Dataset de  │       │    Reward    │       │  Loop de PPO │
│ red teaming  │ ────► │    model     │ ────► │  (o DPO como │
│ + rechazos   │       │  (harmless + │       │  alternativa │
│   seguros    │       │   helpful)   │       │  más liviana)│
└──────────────┘       └──────────────┘       └──────────────┘
```

Dos puntos prácticos que explican por qué esto es costoso, no solo
conceptualmente distinto del fine-tuning ordinario:

- **Reward models especializados por categoría.** En vez de un único
  clasificador de "bueno/malo", suele entrenarse más de un *reward model* —
  uno para odio/violencia, otro para contenido de ciberseguridad, otro para
  riesgo CBRN— y combinar sus puntajes con una ponderación para obtener la
  recompensa final que ve PPO.
- **Costo de memoria de PPO frente a DPO.** La diferencia de arquitectura
  entre ambos pipelines es, en la práctica, la razón de ingeniería más
  concreta detrás del giro de la industria hacia DPO:

  | | Pipeline con PPO | Pipeline con DPO |
  |---|---|---|
  | Modelos en VRAM durante entrenamiento | 4: *policy* (LLM a entrenar), referencia (SFT congelado), *reward model*, crítico | 2: *policy* (LLM a entrenar), referencia (congelado) |
  | Mecanismo de generación | Genera respuestas nuevas en cada paso (RL online) — lento e inestable | Pasadas forward/backward estándar sobre datos de preferencia ya recolectados (offline) |
  | Estabilidad de entrenamiento | Sensible a hiperparámetros (learning rates de *actor*/crítico, banda de *clipping*, peso de KL) | Comparable a una pérdida de clasificación estándar — más estable |
  | Infraestructura | Orquestación distribuida (Ray, DeepSpeed) para alternar generación y entrenamiento | Compatible con el mismo pipeline estándar que se usa para SFT |

  Con PPO, esos 4 modelos activos simultáneamente representan del orden de
  4 veces el consumo de VRAM de una inferencia estándar sobre el modelo
  base, y exigen paralelizar tanto la generación de respuestas como la
  actualización de gradientes. DPO evita ese costo por diseño: como se ve en
  la sección anterior, su pérdida se calcula sobre pares de preferencia ya
  existentes, sin generar nada nuevo durante el entrenamiento.

## Para seguir pensando

1. El *reward model* de seguridad se entrena con datos de *red teaming*
   —prompts adversariales pensados para provocar fallas—. ¿Qué pasa si el
   conjunto de ataques usado para generar esos datos queda desactualizado
   frente a técnicas nuevas? ¿Es un problema que resuelve mejor RLHF o mejor
   DPO, o es independiente del algoritmo de optimización elegido?
2. El *over-refusal* y la *safety alignment degradation* (el otro documento)
   son fallas opuestas del mismo mecanismo: una es demasiada alineación, la
   otra demasiado poca. ¿Qué característica del *reward model* o del dataset
   de entrenamiento controla ese balance, y por qué ese balance nunca puede
   fijarse una sola vez y olvidarse?
3. *Iterative/Online DPO* reintroduce, por fuera del loop de optimización,
   la exploración y la evaluación externa que la pérdida de DPO había
   eliminado. Estructuralmente, ¿en qué se parece esa solución a volver a
   tener un *reward model* separado? ¿Qué es, entonces, lo que DPO realmente
   ahorra frente a PPO cuando se lo usa de forma iterativa: el cómputo, la
   complejidad, o ambos por igual?
