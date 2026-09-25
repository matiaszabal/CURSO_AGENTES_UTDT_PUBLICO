#!/usr/bin/env bash
# Setup de los labs del Módulo 1: crea el venv, instala dependencias y
# arma .env si no existe. Se corre una sola vez por máquina.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creando entorno virtual (.venv)..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Instalando dependencias..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "Se creó .env a partir de .env.example."
  echo "Completalo con tu GOOGLE_API_KEY antes de correr ./run.sh"
else
  echo ".env ya existe — no se tocó."
fi

echo
echo "Setup listo. Probá con: ./run.sh 1"
