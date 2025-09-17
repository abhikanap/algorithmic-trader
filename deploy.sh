#!/bin/bash

# Algorithmic Trading Platform - Deployment Script
# This script automates the deployment of the trading platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="algorithmic-trading"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-localhost:5000}"
VERSION="${VERSION:-latest}"

echo -e "${BLUE}🚀 Algorithmic Trading Platform Deployment${NC}"
echo "=================================================="

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster."
        exit 1
    fi
    
    print_status "Prerequisites check passed ✅"
}

# Build Docker images
build_images() {
    print_status "Building Docker images..."
    
    # Build main trading engine image
    print_status "Building trading engine image..."
    docker build -t "${DOCKER_REGISTRY}/algorithmic-trader:${VERSION}" .
    
    # Build UI dashboard image
    print_status "Building dashboard image..."
    docker build -t "${DOCKER_REGISTRY}/algorithmic-trader-ui:${VERSION}" -f Dockerfile.ui .
    
    print_status "Docker images built successfully ✅"
}

# Push images to registry
push_images() {
    if [[ "${DOCKER_REGISTRY}" != "localhost:5000" ]]; then
        print_status "Pushing images to registry..."
        docker push "${DOCKER_REGISTRY}/algorithmic-trader:${VERSION}"
        docker push "${DOCKER_REGISTRY}/algorithmic-trader-ui:${VERSION}"
        print_status "Images pushed successfully ✅"
    else
        print_warning "Using local registry, skipping push"
    fi
}

# Deploy to Kubernetes
deploy_k8s() {
    print_status "Deploying to Kubernetes..."
    
    # Create namespace and basic resources
    kubectl apply -f k8s/00-namespace.yaml
    
    # Wait for namespace to be ready
    kubectl wait --for=condition=Ready namespace/${NAMESPACE} --timeout=30s
    
    # Deploy databases first
    print_status "Deploying databases..."
    kubectl apply -f k8s/03-databases.yaml
    
    # Wait for databases to be ready
    print_status "Waiting for databases to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/postgres -n ${NAMESPACE}
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n ${NAMESPACE}
    
    # Deploy trading engine
    print_status "Deploying trading engine..."
    kubectl apply -f k8s/01-trading-engine.yaml
    
    # Deploy dashboard
    print_status "Deploying dashboard..."
    kubectl apply -f k8s/02-dashboard.yaml
    
    # Wait for deployments to be ready
    print_status "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/trading-engine -n ${NAMESPACE}
    kubectl wait --for=condition=available --timeout=300s deployment/trading-dashboard -n ${NAMESPACE}
    
    print_status "Kubernetes deployment completed ✅"
}

# Setup monitoring (optional)
setup_monitoring() {
    if [[ "${ENABLE_MONITORING}" == "true" ]]; then
        print_status "Setting up monitoring..."
        
        # Install Prometheus operator (if not already installed)
        if ! kubectl get crd prometheuses.monitoring.coreos.com &> /dev/null; then
            print_status "Installing Prometheus operator..."
            kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
        fi
        
        # Deploy monitoring configuration
        kubectl create configmap prometheus-config --from-file=monitoring/prometheus.yml -n ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
        kubectl create configmap alert-rules --from-file=monitoring/alert_rules.yml -n ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
        
        print_status "Monitoring setup completed ✅"
    else
        print_warning "Monitoring disabled (set ENABLE_MONITORING=true to enable)"
    fi
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check pod status
    echo -e "\n${BLUE}Pod Status:${NC}"
    kubectl get pods -n ${NAMESPACE}
    
    # Check service status
    echo -e "\n${BLUE}Service Status:${NC}"
    kubectl get services -n ${NAMESPACE}
    
    # Get dashboard URL
    if kubectl get ingress trading-dashboard-ingress -n ${NAMESPACE} &> /dev/null; then
        DASHBOARD_URL=$(kubectl get ingress trading-dashboard-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}')
        print_status "Dashboard available at: https://${DASHBOARD_URL}"
    else
        print_status "Dashboard service available internally"
        print_status "To access dashboard locally, run:"
        echo "  kubectl port-forward -n ${NAMESPACE} service/trading-dashboard-service 8501:80"
    fi
    
    print_status "Deployment verification completed ✅"
}

# Main deployment flow
main() {
    echo -e "\nDeployment Configuration:"
    echo "  Namespace: ${NAMESPACE}"
    echo "  Registry: ${DOCKER_REGISTRY}"
    echo "  Version: ${VERSION}"
    echo "  Monitoring: ${ENABLE_MONITORING:-false}"
    echo ""
    
    check_prerequisites
    
    # Ask for confirmation
    echo -e "\n${YELLOW}Do you want to proceed with deployment? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
    
    build_images
    push_images
    deploy_k8s
    setup_monitoring
    verify_deployment
    
    echo -e "\n${GREEN}🎉 Deployment completed successfully!${NC}"
    print_status "Next steps:"
    echo "  1. Configure API keys in the trading-secrets secret"
    echo "  2. Update configuration in trading-config configmap"
    echo "  3. Monitor logs: kubectl logs -f deployment/trading-engine -n ${NAMESPACE}"
    echo "  4. Access dashboard via port-forward or ingress"
}

# Handle script arguments
case "${1:-deploy}" in
    "build")
        check_prerequisites
        build_images
        ;;
    "push")
        check_prerequisites
        push_images
        ;;
    "deploy")
        main
        ;;
    "verify")
        verify_deployment
        ;;
    "clean")
        print_warning "Cleaning up deployment..."
        kubectl delete namespace ${NAMESPACE} --ignore-not-found=true
        print_status "Cleanup completed ✅"
        ;;
    *)
        echo "Usage: $0 {build|push|deploy|verify|clean}"
        echo "  build  - Build Docker images only"
        echo "  push   - Push images to registry"
        echo "  deploy - Full deployment (default)"
        echo "  verify - Verify existing deployment"
        echo "  clean  - Remove deployment"
        exit 1
        ;;
esac
