# Ataques Adversariales de Evasión: FGSM, PGD, GCG y el Espacio Discreto de Tokens

> **Por qué este documento.** El catálogo de amenazas de MAESTRO (Capa 1 →
> Inference-Time Attacks → *Adversarial Inputs*) nombra esta familia de
> ataques sin desarrollar su mecanismo matemático. Este documento junta ese
> desarrollo completo en un solo lugar, para quien quiera profundizar.
>
> **Qué asume ya sabido.** Que entrenar una red neuronal es ajustar sus pesos
> para minimizar una función de pérdida (*loss*), que el **gradiente** de esa
> función respecto a los pesos indica en qué dirección moverlos para que la
> pérdida baje, y que **backpropagation** es el algoritmo que calcula ese
> gradiente propagando el error hacia atrás, capa por capa. Ese mecanismo ya
> está desarrollado en `recursos_aprendizaje/gradiente_finetuning_explicacion.md`
> — acá no se repite, se lo usa como base.
>
> **Qué no cubre.** No es una guía de mitigación operativa fila por fila —esa
> tabla vive en el material de MAESTRO (Capa 1, Security Controls). Este
> documento se queda en el "cómo funciona el ataque".

## La idea en una frase, antes del formalismo

Un ataque de evasión no entrena nada ni toca un solo peso del modelo. Asume
que el modelo ya está entrenado y en producción, congela sus pesos, y usa
exactamente la misma maquinaria de backpropagation que se usó para
entrenarlo —pero apuntada al revés: en vez de preguntar "¿cómo ajusto los
pesos para acertar más?", pregunta "¿cómo cambio la *entrada* para que el
modelo se equivoque exactamente como yo quiero, sin que un humano note el
cambio?".

## Formalización

Si una función `f(x)` (un clasificador, o en un LLM la función que mapea una
secuencia de entrada a una distribución de probabilidad sobre el siguiente
token) asigna a una entrada `x` la salida correcta `y`, el atacante busca una
perturbación mínima `δ` tal que:

- `f(x+δ) ≠ y` — evasión **no dirigida**: cualquier salida incorrecta sirve.
- `f(x+δ) = y_objetivo` — evasión **dirigida**: el atacante elige la salida
  exacta que quiere forzar.

sujeto a que la norma de la perturbación `‖δ‖` esté acotada por un
presupuesto `ε` — un límite que garantiza que `x+δ` siga siendo, para un
observador humano, indistinguible o semánticamente equivalente a `x`. Ese
presupuesto `ε` es la variable de diseño central de todo el ataque: cuanto
más chico, más imperceptible la perturbación; cuanto más grande, más fácil
lograr la evasión pero más riesgo de que un humano note algo raro.

## Clasificación según el conocimiento del atacante

### White-box: el atacante tiene los planos completos

Acceso a pesos, arquitectura y gradientes — condición realista para modelos
open-weight que un atacante puede correr localmente, aunque el objetivo
final sea un servicio cerrado con la misma arquitectura o una similar. Con
eso puede calcular la perturbación óptima directamente:

- **FGSM (Fast Gradient Sign Method)**: un solo paso en la dirección del
  signo del gradiente de la pérdida respecto a la *entrada* (no respecto a
  los pesos, que es lo que se calcularía en entrenamiento normal). En su
  versión no dirigida (Goodfellow et al., 2014), el objetivo es *alejarse*
  de la etiqueta correcta `y`, así que el paso sube la pérdida respecto a
  esa etiqueta:

  ```
  δ = ε · signo(∇x Loss(Modelo(x), y))
  x_adversarial = x + δ
  ```

  En la versión dirigida hacia una clase `y_objetivo` elegida por el
  atacante, el signo se invierte —el paso *baja* la pérdida respecto al
  objetivo, en vez de subirla respecto a la etiqueta real—:
  `δ = −ε · signo(∇x Loss(Modelo(x), y_objetivo))`. Rápido (un solo paso),
  pero perturbaciones más gruesas y más fáciles de filtrar que las de
  métodos iterativos.

- **PGD (Projected Gradient Descent)**: la versión iterativa de FGSM —da
  varios pasos chicos en la dirección del gradiente y, después de cada paso,
  *proyecta* la entrada perturbada de vuelta a la bola de radio `ε` (si el
  paso se pasó del presupuesto permitido, la recorta). Más costoso que FGSM,
  pero produce perturbaciones más robustas — el estándar de facto para
  evaluar robustez adversarial en la literatura.

- **C&W (Carlini & Wagner)**: en vez de fijar `ε` de antemano y buscar la
  mejor perturbación dentro de ese presupuesto, formula el problema como una
  optimización que busca directamente la perturbación de **norma mínima**
  con alta tasa de éxito. Más costoso computacionalmente que FGSM/PGD, pero
  más preciso — suele usarse como el ataque de referencia para *romper* una
  defensa que se declara robusta.

### Black-box: el atacante solo ve entradas y salidas

El caso realista contra la mayoría de las APIs comerciales de LLMs, donde no
hay acceso a pesos ni gradientes:

- **Query-based attacks**: estimar el gradiente por diferencias finitas —
  consultar el modelo repetidamente con variaciones chicas de la entrada y
  observar cómo cambia la salida, reconstruyendo una aproximación del
  gradiente sin nunca tener acceso a él directamente.
- **Transferability attacks**: entrenar un modelo *sustituto* por
  distillation sobre las salidas del modelo objetivo (consultarlo mucho y
  usar esas respuestas como dataset de entrenamiento para un modelo propio),
  craftear el ejemplo adversarial en white-box contra ese sustituto, y
  transferir el resultado al modelo objetivo real. Funciona porque
  perturbaciones craftadas contra un modelo suelen transferir con éxito
  parcial a otros modelos con arquitectura o entrenamiento similar — un
  hecho empírico, no garantizado, pero consistentemente observado.

## El problema específico de texto: el espacio de tokens es discreto

La técnica nació en visión por computadora (el ejemplo clásico: una señal de
Stop con ruido imperceptible para un humano, clasificada como Límite de
Velocidad) y tiene variantes documentadas en audio (comandos ultrasónicos
inaudibles pero transcriptos por el modelo) y en malware (inyección de bytes
en secciones muertas de un binario para evadir un clasificador de EDR) — se
mencionan solo como contexto de origen, no son la superficie relevante para
un sistema agéntico basado en LLM.

Lo que sí importa acá es la variante texto/LLM, y ahí aparece una restricción
que no existe en imagen o audio: **no se puede simplemente "sumar δ" sobre el
input** como se suma ruido a los píxeles de una imagen, porque no existe un
token "entre" dos tokens del vocabulario — el espacio es discreto, no
continuo.

**GCG (Greedy Coordinate Gradient)** es la respuesta a esa restricción, y es
el caso de frontera entre esta categoría y *Jailbreaking* que vale la pena
nombrar con precisión: usa el gradiente del modelo (white-box) para guiar una
**búsqueda discreta** — en cada paso evalúa qué sustitución de un token del
sufijo del prompt reduce más la pérdida hacia la respuesta objetivo, y
avanza greedy sobre esa dirección. El resultado es un sufijo de aspecto
arbitrario —a menudo texto sin sentido semántico para un humano— que,
concatenado al prompt, hace que el modelo cumpla una instrucción que sus
políticas deberían rechazar.

La distinción formal que conviene retener: el *método* de GCG es Adversarial
Inputs en estado puro (optimización basada en gradiente sobre la geometría
de la función, no manipulación semántica); el *objetivo* de GCG es el de un
Jailbreak (bypassear alineamiento). Es la prueba de que la distinción entre
las dos categorías es por mecanismo y objetivo, no una partición que
garantice que cada ataque real caiga limpiamente en una sola casilla.

Otras manifestaciones específicas de texto, sin necesidad de gradiente:

- **Caracteres Unicode invisibles o de ancho cero** insertados entre tokens
  de una palabra prohibida — rompen la tokenización esperada por el
  clasificador de seguridad sin alterar la lectura humana del texto.
- **Homoglifos**: sustituir caracteres por otros visualmente idénticos de
  otro alfabeto Unicode (por ejemplo, una "a" cirílica en vez de una "a"
  latina) — el ojo humano no distingue la diferencia, pero el tokenizador y
  cualquier filtro basado en coincidencia de strings sí la tratan como un
  carácter distinto.

## Estrategias de mitigación y su límite estructural

| Estrategia | Cómo funciona | Límite |
|---|---|---|
| **Adversarial training** | Incluir ejemplos adversariales correctamente etiquetados en el reentrenamiento | Efectivo pero costoso, y solo cubre las clases de perturbación representadas en el entrenamiento — no generaliza a un método de ataque nuevo |
| **Input sanitization / denoising** | Normalización Unicode, detección de sufijos de baja probabilidad, cuantización previa a la inferencia | Es, en sí mismo, un clasificador más — atacable con suficiente iteración adversarial, el mismo límite estructural que la sanitización de prompt injection |
| **Gradient masking / obfuscation** | Dificultar el cálculo del gradiente al atacante white-box (ocultar logits crudos) | No da seguridad completa: el ataque sigue siendo viable vía transferability desde un modelo sustituto |
| **Certified / provable robustness** | Métodos como *Randomized Smoothing*, que garantizan formalmente que la predicción no cambia dentro de un radio `ε` | Única categoría con garantía matemática en lugar de evidencia empírica, pero computacionalmente cara y todavía poco adoptada en LLMs de producción a la escala necesaria |

## Cómo se conecta con el resto de MAESTRO

Adversarial Inputs es mecánicamente distinto de Data/Model Poisoning
(también en Capa 1 de MAESTRO): Poisoning corrompe el modelo *durante el
entrenamiento*; Adversarial Inputs actúa exclusivamente en tiempo de
inferencia, sin tocar un solo peso, y asume el modelo ya desplegado. También
se distingue de **Model Inversion** (la otra amenaza de esta subcategoría en
MAESTRO): Model Inversion busca *reconstruir* información memorizada del
corpus de entrenamiento a partir de las salidas del modelo; Adversarial
Inputs busca *forzar* una salida específica manipulando la entrada, sin que
al atacante le interese qué memorizó el modelo.

## Para seguir pensando

1. GCG produce sufijos que un humano lee como "texto sin sentido". Si un
   sistema agéntico filtrara cualquier input con baja probabilidad
   lingüística (perplejidad alta), ¿cerraría GCG por completo? ¿Qué le
   pasaría a ese mismo filtro frente a Jailbreaking semántico clásico
   (roleplay, framing de subtarea legítima)?
2. La tabla de mitigaciones muestra que casi todas son, en el fondo, "otro
   clasificador" —con el mismo problema de fondo que intentan resolver.
   ¿Por qué *Certified/provable robustness* escapa a esa crítica, y por qué
   creés que no es todavía el estándar en producción?
