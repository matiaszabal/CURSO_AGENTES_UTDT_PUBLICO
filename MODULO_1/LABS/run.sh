#!/usr/bin/env bash
# Corre cualquier ejemplo de los labs del Módulo 1 con el venv activado y las
# variables de .env cargadas. Requiere haber corrido ./setup.sh antes.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "No existe .venv — corré ./setup.sh primero." >&2
  exit 1
fi
if [ ! -f .env ]; then
  echo "No existe .env — corré ./setup.sh y completalo con tu GOOGLE_API_KEY." >&2
  exit 1
fi

source .venv/bin/activate
set -a
source .env
set +a

uso() {
  cat >&2 <<EOF
Uso: ./run.sh {1|2|3|aside|all}

  1      Versión A determinista (no necesita API key)
  2      Versión B, workflow con ADK2
  3      Versión C, agente ADK2 con HITL
  aside  Ejercicio opcional — agente de investigación
  all    Versiones A, B y C en secuencia
EOF
  exit 1
}

case "${1:-}" in
  1) python3 lab01_v_a_determinista.py ;;
  2) python3 lab01_v_b_workflow.py ;;
  3) python3 lab01_v_c_agente_hitl.py ;;
  aside) python3 lab01_ej2_investigacion.py ;;
  all)
    python3 lab01_v_a_determinista.py
    python3 lab01_v_b_workflow.py
    python3 lab01_v_c_agente_hitl.py
    ;;
  *) uso ;;
esac
