# Makefile for Password-Advisor
SHELL := /bin/bash

# --- Configuration ---
NAMESPACE ?= password-advisor
K8S_DIR ?= k8s

# Default Docker image tags (update if you build new versions)
CHECKER_IMAGE ?= shah10d/checker:v2.4 
ADVISOR_IMAGE ?=shah10d/advisor:v2.3 
FRONTEND_IMAGE ?= shah10d/frontend:v2.2

# ---------- PHONY targets ----------
.PHONY: all clean namespace create-secret db wait-db job deploy-app ingress test test-db test-ingress build-images push-images logs reset-db

# Default: full deployment flow
all: namespace create-secret db wait-db job deploy-app ingress test
	@echo
	@echo "Deployment completed successfully."
	@echo "To access the application, run: make test-ingress"
	@echo

# Create namespace
namespace:
	@echo "Creating namespace '$(NAMESPACE)'..."
	kubectl apply -f $(K8S_DIR)/namespace.yaml

# Create Kubernetes secret interactively
create-secret:
	@echo "Setting up database secret (user=postgres, db=passworddb)"
	@read -s -p "Enter POSTGRES_PASSWORD: " pwd; echo; \
	if [ -z "$$pwd" ]; then echo "Error: Password is required"; exit 1; fi; \
	kubectl create secret generic pg-secret -n $(NAMESPACE) \
		--from-literal=POSTGRES_USER="postgres" \
		--from-literal=POSTGRES_PASSWORD="$$pwd" \
		--from-literal=POSTGRES_DB="passworddb" \
		--dry-run=client -o yaml | kubectl apply -f -

# Deploy PostgreSQL (PVC, Deployment, Service)
db:
	@echo "Deploying PostgreSQL (PVC, Deployment, Service)..."
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/postgres-pvc.yaml
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/postgres-deploy.yaml
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/postgres-svc.yaml

# Wait for PostgreSQL to be ready
wait-db:
	@echo "Waiting for PostgreSQL to be ready..."
	kubectl rollout status deployment/postgres -n $(NAMESPACE) --timeout=120s

# Run job to load password hashes
job:
	@echo "Starting load-hashes job..."
	-kubectl delete job load-hashes -n $(NAMESPACE) --ignore-not-found
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/load-hashes-job.yaml
	@echo "Waiting for job to complete (up to 180s)..."
	@for i in $$(seq 1 90); do \
		S=$$(kubectl get job load-hashes -n $(NAMESPACE) -o jsonpath='{.status.succeeded}' 2>/dev/null || echo 0); \
		if [ "$$S" = "1" ]; then echo "Job completed successfully"; break; fi; \
		echo "  waiting... ($$i/90)"; sleep 2; \
	done; \
	if [ "$$S" != "1" ]; then \
		echo "Error: Job did not complete in time"; \
		kubectl get pods -n $(NAMESPACE); \
		kubectl logs -n $(NAMESPACE) -l job-name=load-hashes --tail=50 || true; \
		exit 1; \
	fi

# Deploy microservices
deploy-app:
	@echo "Deploying microservices (checker, advisor, frontend)..."
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/checker-svc.yaml
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/checker-deploy.yaml
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/advisor-svc.yaml
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/advisor-deploy.yaml
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/frontend-svc.yaml
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/frontend-deploy.yaml
	@sleep 10
	@kubectl get pods -n $(NAMESPACE)

# Apply Ingress
ingress:
	@echo "Applying Ingress resource..."
	kubectl apply -n $(NAMESPACE) -f $(K8S_DIR)/ingress.yaml
	@echo "Ingress status:"
	@kubectl get ingress -n $(NAMESPACE)

# Basic status check
test:
	@echo "Current resources in namespace '$(NAMESPACE)':"
	@kubectl get pods -n $(NAMESPACE)
	@kubectl get svc -n $(NAMESPACE)

# Test database content
test-db:
	@echo "Querying leaked_passwords table..."
	@PGUSER=$$(kubectl get secret pg-secret -n $(NAMESPACE) -o jsonpath='{.data.POSTGRES_USER}' | base64 -d 2>/dev/null || echo "postgres"); \
	PGDB=$$(kubectl get secret pg-secret -n $(NAMESPACE) -o jsonpath='{.data.POSTGRES_DB}' | base64 -d 2>/dev/null || echo "passworddb"); \
	POD=$$(kubectl get pod -n $(NAMESPACE) -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$POD" ]; then echo "Error: PostgreSQL pod not found"; exit 1; fi; \
	kubectl exec -n $(NAMESPACE) "$$POD" -- psql -U "$$PGUSER" -d "$$PGDB" -c "SELECT count(*) AS leaked_count FROM leaked_passwords;"

# Get frontend URL
test-ingress:
	@echo "Checking if ingress-nginx controller is installed..."
	@if ! kubectl get svc ingress-nginx-controller -n ingress-nginx >/dev/null 2>&1; then \
		echo " Error: ingress-nginx-controller service not found."; \
		echo " Run: minikube addons enable ingress"; \
		echo "   Then wait ~30 seconds for it to start."; \
		exit 1; \
	fi
	@echo "To access the frontend, open the URL below."
	@echo "Example: http://127.0.0.1:32123/checker.html"
	@echo ""
	@minikube service ingress-nginx-controller -n ingress-nginx --url
	@echo ""

# Reset database (delete PVC to reinitialize with new credentials)
reset-db:
	@echo "Deleting PVC 'pg-data-pvc' to reset database credentials..."
	-kubectl delete pvc pg-data-pvc -n $(NAMESPACE) --ignore-not-found
	@echo "PVC deleted. Next 'make db' will initialize with current secret."

# Clean up entire namespace
clean:
	@echo "Deleting namespace '$(NAMESPACE)'..."
	-kubectl delete namespace $(NAMESPACE) --ignore-not-found
	@echo "Cleanup initiated."

# Build Docker images
build-images:
	@echo "Building Docker images..."
	docker build -t $(CHECKER_IMAGE) ./checker
	docker build -t $(ADVISOR_IMAGE) ./advisor
	docker build -t $(FRONTEND_IMAGE) ./frontend

# Push Docker images
push-images:
	@echo "Pushing Docker images to registry..."
	docker push $(CHECKER_IMAGE)
	docker push $(ADVISOR_IMAGE)
	docker push $(FRONTEND_IMAGE)

# Show logs for debugging
logs:
	@echo "Ingress controller logs (last 100 lines):"
	@kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail=100 || echo "No logs found"
	@echo "Advisor logs:"
	@kubectl logs -n $(NAMESPACE) deploy/advisor --tail=100 || echo "No logs found"
	@echo "Checker logs:"
	@kubectl logs -n $(NAMESPACE) deploy/checker --tail=100 || echo "No logs found"