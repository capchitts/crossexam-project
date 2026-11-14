# Step 8: cloud

**What step 7 showed:** the whole system, visible -- logs, metrics, queue depth, a task history. Still one laptop.

**The goal of this step:** write down what running it on a cluster would take, as real code, and check that code is correct -- without touching a real cloud account.

## What each Terraform file is for

| File | What it defines |
|---|---|
| `foundation.tf` | The VPC, a subnet with Private Service Access (so Cloud SQL and the cluster talk without public IPs), Cloud NAT (so pods can reach the internet to call Gemini), a Cloud Storage bucket for documents, the Artifact Registry repository for container images, and three Secret Manager secrets: the database password (generated), the Gemini key, and a LangSmith key placeholder. |
| `gke.tf` | The GKE cluster itself, the `crossexam` namespace and its config map, and KEDA (installed by Helm) -- the autoscaler that watches queue depth instead of CPU, so a month-end backlog adds workers automatically. |
| `iam.tf` | A single service account the workload runs as, scoped to exactly what it needs (pull images, write to the bucket, read the secrets, call Vertex AI) -- and separately, Workload Identity Federation for GitHub Actions, so `deploy.yml` can authenticate to Google Cloud with **no JSON key stored anywhere**. |
| `data.tf`, `main.tf`, `ops.tf`, `outputs.tf`, `variables.tf` | Provider configuration, input variables (project id, region), and the outputs `deploy.yml` reads (the workload identity provider, the deployer service account). |

## What each Kubernetes overlay is for

| Overlay | What it holds |
|---|---|
| `base/` | The namespace, service accounts, and `secrets.yaml` -- references to the Secret Manager secrets above, mounted as files (see `scripts/docker-entrypoint.sh`'s own comment on this: a deployment gives a secret a mount even when that deployment does not use it, because a mount fails on a secret with no version). |
| `app/` | `api.yaml`, `web.yaml`, `workers.yaml` (the reader and agent pools, the ones step 5 first ran locally), `flower.yaml`, and `cronjobs.yaml` (the periodic sweeps step 5's `reap_stale` and step 7's nightly quality check would run as, on a real cluster). |
| `migrate/` | A one-shot `Job` that runs the database migration before the app pods start. |
| `public/` | An `Ingress`, optional (`PUBLIC_WEB=true` in `deploy.yml`), for a demo that needs the web screen reachable from outside the cluster. |

## Run it

```bash
make validate
```
```
cd infra/terraform && terraform init -backend=false -input=false && terraform validate && terraform fmt -check -diff
...
Terraform has been successfully initialized!
Success! The configuration is valid.

--- infra/k8s/app ---
renders OK
--- infra/k8s/base ---
renders OK
--- infra/k8s/migrate ---
renders OK
--- infra/k8s/public ---
renders OK
```
`-backend=false` means Terraform never tries to reach a remote state backend; `terraform validate` only checks that the configuration is internally consistent (types, references, required arguments) -- it needs no credentials and makes no API calls. `kubectl kustomize` only reads and merges local YAML files; it never contacts a cluster.

## A doubt worth saying out loud

*"If nothing was deployed, how do we know this would actually work on a real cluster?"* We don't, fully -- and this step says so rather than pretending otherwise. `terraform validate` catches wrong types, missing required fields, and broken references between resources; it does **not** catch a wrong IAM permission, a quota limit, or a region that doesn't support a feature, any of which only a real `terraform plan` against a real project would surface. The honest claim here is narrower than main's own README perhaps implies at a glance: this code is internally consistent, not proven on Google Cloud.

## What was not run

- `terraform plan` / `apply` -- needs a real project, billing, and `terraform.tfvars` (the example file shows the shape; no real one exists in this branch).
- `kubectl apply --dry-run=client` -- needs a live cluster to discover API groups against, even for a dry run; not available without one.
- `.github/workflows/*.yml` through `actionlint` or a real GitHub Actions run.
- The GKE cluster, KEDA autoscaling a real backlog, the ingress serving real traffic -- everything these files describe, running.

## What it still gets wrong

Nothing, by this step's own stated goal -- but the goal itself is narrow: *this code is valid*, not *this system runs the same way on a cluster as it does on one laptop*. That gap is real, and closing it needs the thing this step deliberately does not do: an actual cloud project, a yes, and someone watching the bill.
