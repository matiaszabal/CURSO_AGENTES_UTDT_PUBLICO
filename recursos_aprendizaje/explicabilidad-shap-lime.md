# SHAP, LIME y Explainability Poisoning: por qué la explicación no es la decisión

> **Por qué este documento.** El catálogo de amenazas de MAESTRO (Capa 5 →
> Monitoring Evasion → *Explainability Poisoning*) nombra que estas
> herramientas pueden ser manipuladas para dar una justificación engañosa de
> una decisión, sin desarrollar cómo funcionan SHAP y LIME ni el mecanismo
> exacto del ataque. Este documento cubre ambas cosas.
>
> **Qué asume ya sabido.** Los conceptos generales de MAESTRO Capa 5
> (Evaluation & Observability) y la distinción, ya vista en el curso, entre
> un sistema que actúa (agente) y un sistema que solo explica por qué actuó
> (la capa de explicabilidad) — acá se asume esa distinción como dada, y se
> desarrolla por qué esa segunda capa es, ella misma, atacable.

## El problema que SHAP y LIME intentan resolver

Un modelo de machine learning complejo (una red neuronal, un ensemble de
árboles) toma una decisión —aprueba un crédito, clasifica un email como
spam, recomienda una acción— sin que sea evidente, mirando la arquitectura,
*por qué* llegó a esa conclusión para un caso puntual. **SHAP** y **LIME**
son las dos herramientas más usadas de la familia *post-hoc explainability*:
no cambian el modelo ni lo hacen más transparente por diseño, generan una
explicación *después* de que la predicción ya se hizo, para esa predicción
puntual.

### SHAP (SHapley Additive exPlanations)

Calcula, para una predicción puntual, cuánto contribuyó cada feature de
entrada al resultado, repartiendo el "crédito" de la predicción entre las
features con una idea tomada de la teoría de juegos: los **valores de
Shapley**, que originalmente responden "si un grupo de jugadores genera un
valor conjunto, ¿cuánto le corresponde a cada jugador según su contribución
marginal promedio en todas las combinaciones posibles del grupo?". Aplicado
a un modelo, cada feature es un "jugador" y la predicción es el "valor
generado". El resultado es una lista de features con un número al lado que
dice cuánto empujó cada una la predicción hacia arriba o hacia abajo
respecto de un valor base.

### LIME (Local Interpretable Model-agnostic Explanations)

Hace algo relacionado pero mecánicamente distinto: genera muchas **variantes
perturbadas** de la entrada puntual que se quiere explicar (por ejemplo,
para un texto, versiones con algunas palabras removidas o reemplazadas),
corre el modelo real sobre esas variantes, y ajusta un **modelo simple e
interpretable** (típicamente una regresión lineal) que aproxime el
comportamiento del modelo complejo *solo en ese vecindario local* alrededor
de la entrada original. La explicación que devuelve es la de ese modelo
simple —no la del modelo real—, con la promesa de que en un entorno chico
alrededor del punto de interés, esa aproximación lineal es razonablemente
fiel.

## Dónde está la grieta

Tanto SHAP como LIME comparten una propiedad que, mirada con cuidado, es una
vulnerabilidad: **ninguna de las dos audita la decisión real del modelo
sobre tráfico de producción**. Auditan el comportamiento del modelo sobre un
conjunto de inputs **sintéticos**, generados específicamente para producir
la explicación —las variantes perturbadas de LIME, las coaliciones de
features que SHAP evalúa para calcular la contribución marginal de cada
una— y esos inputs sintéticos son, en general, **estadísticamente
distinguibles** de un input genuino de producción (perturbaciones
artificiales, combinaciones de features que no ocurrirían naturalmente,
patrones de missingness poco comunes).

Eso abre una posibilidad concreta: un modelo puede, en principio, aprender a
reconocer "esto no es tráfico real, esto es una consulta generada por un
algoritmo de explicabilidad" y comportarse distinto —más neutral, más
benigno, sin el sesgo real que tiene en producción— exactamente en esa
situación, sin alterar en absoluto su comportamiento ante inputs de
producción genuinos.

## El ataque, verificado empíricamente

Esto no es una posibilidad teórica: **Slack et al. (2020, "Fooling LIME and
SHAP: Adversarial Attacks on Post hoc Explanation Methods")** lo
demostraron construyendo un clasificador entrenado deliberadamente con dos
comportamientos según el input que recibe:

- Ante datos de **producción reales** (por ejemplo, decisiones de crédito
  usando raza como feature de forma discriminatoria), discrimina con
  normalidad.
- Ante las **muestras perturbadas que generan LIME o SHAP** para explicar
  ese mismo modelo, el clasificador las reconoce como tales (por ser
  estadísticamente distinguibles del tráfico real) y responde de forma
  benigna, sin usar la feature discriminatoria.

El resultado: la herramienta de auditoría reporta un modelo limpio,
"explicando" fielmente una versión del modelo que nunca es la que
efectivamente toma decisiones sobre usuarios reales. La herramienta de
explicabilidad termina auditando una versión maquillada del modelo, no el
modelo que efectivamente decide.

## Por qué esto es un ataque distinto de manipular la decisión en sí

Vale la pena remarcar la distinción con Adversarial Inputs (Capa 1, ver
`recursos_aprendizaje/adversarial-ml-ataques-evasion.md`): ahí el atacante
manipula la *entrada* para forzar una salida distinta del modelo. Acá el
modelo puede seguir tomando exactamente la misma decisión de siempre sobre
tráfico real —el ataque no busca cambiar *qué* decide el modelo, busca
cambiar *qué explicación se da* de esa decisión. Es un ataque contra la capa
de rendición de cuentas, no contra la decisión subyacente.

| Eje | Adversarial Inputs (Capa 1) | Explainability Poisoning (Capa 5) |
|---|---|---|
| Qué se manipula | La entrada que recibe el modelo en producción | El comportamiento del modelo específicamente frente a queries de un algoritmo de explicabilidad |
| Objetivo del atacante | Forzar una salida distinta a la esperada | Que la explicación reportada no refleje el comportamiento real del modelo |
| El modelo cambia su decisión de producción | Sí, esa es la finalidad del ataque | No necesariamente — puede seguir decidiendo igual, solo "miente" al ser auditado |
| Quién ejecuta el ataque | Un atacante externo, por input | Típicamente, quien entrena o controla el modelo desde el origen |

## Cómo se conecta con el resto de MAESTRO

Este mecanismo es la razón por la que MAESTRO agrupa Explainability
Poisoning junto con Behavioral Mimicry y Slow & Low Attacks dentro de
*Monitoring Evasion* (Capa 5): las tres atacan la capacidad de detectar
comportamiento anómalo, cada una por un eje distinto —forma, tiempo, y en
este caso, la propia instrumentación de auditoría—. También reaparece, con
otro nombre, en **Core-9 (Agent Untraceability)** del catálogo AIVSS: ahí se
agrupa como *Explainability Artifact Poisoning* junto con la
irreconstructibilidad de la cadena de autorización —porque ambas atacan la
misma propiedad de fondo, la capacidad de reconstruir *por qué* pasó lo que
pasó, solo que una la ataca destruyendo el registro y la otra falsificando
la explicación que se da en su lugar.

## Para seguir pensando

1. Si SHAP y LIME auditan comportamiento sobre inputs sintéticos que un
   modelo puede aprender a reconocer, ¿qué propiedad tendría que tener un
   método de auditoría para no ser vulnerable a este mismo ataque? (Pista:
   pensá en qué pasa si la auditoría se corre sobre una muestra de tráfico
   de producción real, en vez de perturbaciones generadas ad-hoc.)
2. El caso de Slack et al. asume que quien entrena el modelo es también
   quien quiere ocultar su comportamiento discriminatorio. ¿Cambia el
   análisis si el atacante es un tercero que solo tiene acceso de query al
   modelo (black-box), como en los ataques de evasión de
   `adversarial-ml-ataques-evasion.md`? ¿Sigue siendo viable el mismo
   ataque?
