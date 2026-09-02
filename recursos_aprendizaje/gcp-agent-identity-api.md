---
name: gcp-agent-identity-api
description: iamconnectors.googleapis.com es la API legacy de Agent Identity/SPIFFE en GCP, reemplazada por agentidentity.googleapis.com — la legacy da PERMISSION_DENIED aunque seas Owner
metadata:
  type: reference
---

`iamconnectors.googleapis.com` (IAM Connectors API) es la API **legacy** para gestionar auth providers / agent identities en GCP — el mismo dominio de [[gcp-sandbox-project|Agent Identity + SPIFFE]] que se trabajó en el experimento Caveman XP1 (ver `../projects/-home-matias-NV-PROYECTOS-DEMOS-CAVEMAN/memory/project-caveman-xp1.md`).

**Ya fue reemplazada por `agentidentity.googleapis.com`** (Agent Identity API). Durante la migración ambas conviven, pero la legacy quedó restringida: intentar `gcloud services enable iamconnectors.googleapis.com` da `PERMISSION_DENIED` (`servicemanagement.services.bind`) **incluso con rol `roles/owner`** en el proyecto — no es un problema de permisos del usuario, es la API vieja bloqueada para nuevas habilitaciones.

**Acción correcta**: habilitar `agentidentity.googleapis.com` en su lugar — esa sí se habilita sin fricción. Piezas base que la acompañan: `iam.googleapis.com`, `iamcredentials.googleapis.com` (impersonation/WIF).

Confirmado en el proyecto `sandbox-ai-zabaljauregui` (2026-08-28, ver [[gcp-sandbox-project]]).
