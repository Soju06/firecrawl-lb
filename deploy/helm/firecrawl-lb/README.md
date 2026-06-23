# firecrawl-lb Helm Chart

Production Helm chart for `firecrawl-lb`, a Firecrawl API load balancer with
account pooling, usage tracking, dashboard access, optional PostgreSQL, metrics,
tracing, ingress, autoscaling, and migration hooks.

## Install

```bash
helm dependency build deploy/helm/firecrawl-lb
helm upgrade --install firecrawl-lb deploy/helm/firecrawl-lb \
  -f deploy/helm/firecrawl-lb/values-bundled.yaml
```

For production with an external database and externally managed secrets:

```bash
helm dependency build deploy/helm/firecrawl-lb
helm upgrade --install firecrawl-lb deploy/helm/firecrawl-lb \
  -f deploy/helm/firecrawl-lb/values-prod.yaml \
  --set externalDatabase.existingSecret=firecrawl-lb-db \
  --set auth.existingSecret=firecrawl-lb-app
```

Published chart installs use:

```bash
helm install firecrawl-lb oci://ghcr.io/soju06/charts/firecrawl-lb
```

## Defaults

- Image: `ghcr.io/soju06/firecrawl-lb`
- Service port: `2465`
- Container data directory: `/var/lib/firecrawl-lb`
- Encryption key path: `/var/lib/firecrawl-lb/encryption.key`
- Environment prefix: `FIRECRAWL_LB_`
- Bundled database: Bitnami PostgreSQL, enabled by default

## Common Values

- `image.repository`, `image.tag`, `image.digest`
- `service.type`, `service.port`
- `ingress.enabled`, `ingress.hosts`, `ingress.tls`
- `postgresql.enabled`
- `externalDatabase.url`, `externalDatabase.existingSecret`
- `auth.existingSecret`, `auth.encryptionKey`
- `metrics.enabled`, `metrics.serviceMonitor.enabled`
- `tracing.enabled`, `tracing.endpoint`
- `autoscaling.enabled`
- `networkPolicy.enabled`
- `migration.enabled`, `migration.schemaGate.enabled`

## Database Secrets

When `auth.existingSecret` is set, the secret must contain:

```text
database-url
encryption-key
```

When `externalDatabase.existingSecret` is set without `auth.existingSecret`,
the external database secret supplies `database-url`, while the chart-managed
application secret contains the encryption key.

Generate an encryption key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Verification

```bash
helm dependency build deploy/helm/firecrawl-lb
helm lint deploy/helm/firecrawl-lb
helm test firecrawl-lb -n <namespace>
kubectl port-forward svc/firecrawl-lb 2465:2465 -n <namespace>
curl -i http://127.0.0.1:2465/health/ready
```
