# 🧪 Comprehensive Testing & Debugging Guide

## Table of Contents
1. [Quick Start Testing](#quick-start-testing)
2. [Performance Optimized Startup](#performance-optimized-startup)
3. [Individual Service Testing](#individual-service-testing)
4. [Integration Testing](#integration-testing)
5. [Debugging Techniques](#debugging-techniques)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Performance Monitoring](#performance-monitoring)
8. [Advanced Testing Scenarios](#advanced-testing-scenarios)

---

## 🚀 Quick Start Testing

### Fastest Platform Test (Optimized Startup)
```bash
# High-performance startup with parallel builds and caching
cd microservices
./fast-startup.sh test

# This will:
# ✅ Build all images in parallel with caching
# ✅ Start services in optimized sequence
# ✅ Run comprehensive tests
# ✅ Show performance metrics
# ⚡ Complete in ~30-60 seconds vs 5+ minutes
```

### Quick Service Health Check
```bash
# Fast health check for all services
curl -s http://localhost:8001/health && echo " ✅ Core Service"
curl -s http://localhost:8002/health && echo " ✅ Market Service"
docker exec trading-redis redis-cli ping && echo " ✅ Redis"
```

---

## ⚡ Performance Optimized Startup

### 🏎️ Fast Startup Options

#### 1. Parallel Build Only
```bash
./fast-startup.sh build
# Builds all images in parallel with caching
```

#### 2. Optimized Service Start
```bash
./fast-startup.sh start
# Starts services in optimal sequence
```

#### 3. Performance Metrics
```bash
./fast-startup.sh metrics
# Shows resource usage and response times
```

#### 4. Clean Start
```bash
./fast-startup.sh clean
# Removes all containers and cached data
```

### 🔧 Performance Features

- **Parallel Docker Builds**: All services build simultaneously
- **Multi-Stage Caching**: Reuses layers between builds
- **BuildKit Optimization**: Advanced Docker build features
- **Optimized Startup Sequence**: Services start in dependency order
- **Resource Limits**: Prevents memory/CPU overconsumption
- **Health Check Optimization**: Faster service readiness detection

---

## 🔍 Individual Service Testing

### Core Service Testing
```bash
# Full core service test
./test-scripts/test-service.sh core-service

# Manual endpoint testing
curl -X GET http://localhost:8001/health
curl -X GET http://localhost:8001/models/signal-types
curl -X POST http://localhost:8001/validate/signal \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "signal_type": "BUY", "confidence": 0.85}'
```

### Market Service Testing  
```bash
# Full market service test
./test-scripts/test-service.sh market-service

# Manual endpoint testing
curl -X GET http://localhost:8002/health
curl -X GET http://localhost:8002/quote/AAPL
curl -X GET http://localhost:8002/quotes/AAPL,GOOGL,MSFT
curl -X GET http://localhost:8002/historical/AAPL?days=30
```

### Redis Testing
```bash
# Redis connectivity test
docker exec trading-redis redis-cli ping
docker exec trading-redis redis-cli info memory
docker exec trading-redis redis-cli config get maxmemory
```

---

## 🔗 Integration Testing

### Full Integration Test
```bash
# Comprehensive integration test
./test-scripts/test-integration.sh

# Test specific integration scenarios
./test-scripts/test-integration.sh validation
./test-scripts/test-integration.sh market-data
./test-scripts/test-integration.sh performance
```

### Service Communication Testing
```bash
# Test service-to-service communication
curl -X POST http://localhost:8002/validate-and-quote \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "signal_type": "BUY"}'

# Test Redis caching
curl -X GET http://localhost:8002/quote/AAPL  # First call (no cache)
curl -X GET http://localhost:8002/quote/AAPL  # Second call (cached)
```

---

## 🐛 Debugging Techniques

### 1. Service Logs Analysis

#### Real-time Log Monitoring
```bash
# All services
docker-compose -f core-optimized.yml logs -f

# Specific service
docker-compose -f core-optimized.yml logs -f core-service
docker-compose -f core-optimized.yml logs -f market-service
docker-compose -f core-optimized.yml logs -f redis
```

#### Log Analysis Commands
```bash
# Search for errors
docker-compose -f core-optimized.yml logs | grep -i error

# Search for specific patterns
docker-compose -f core-optimized.yml logs | grep -E "(failed|exception|error)"

# Service startup sequence
docker-compose -f core-optimized.yml logs --since=5m | grep -E "(Starting|Started|Ready)"
```

### 2. Container Inspection

#### Container Status
```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Detailed container inspection
docker inspect trading-core-service
docker inspect trading-market-service
docker inspect trading-redis
```

#### Resource Usage
```bash
# Real-time resource monitoring
docker stats

# Container resource limits
docker inspect trading-core-service | jq '.[0].HostConfig.Memory'
docker inspect trading-market-service | jq '.[0].HostConfig.Memory'
```

### 3. Network Debugging

#### Network Connectivity
```bash
# Test inter-service connectivity
docker exec trading-market-service curl -s http://core-service:8001/health
docker exec trading-core-service ping redis

# Network inspection
docker network inspect microservices_trading-network
```

#### Port Accessibility
```bash
# Check if ports are accessible
netstat -tlnp | grep :8001
netstat -tlnp | grep :8002
netstat -tlnp | grep :6379

# Test external connectivity
curl -I http://localhost:8001/health
curl -I http://localhost:8002/health
```

### 4. Service-Specific Debugging

#### Core Service Debug
```bash
# Check model validation
curl -v -X POST http://localhost:8001/validate/signal \
  -H "Content-Type: application/json" \
  -d '{"symbol": "INVALID", "signal_type": "INVALID"}'

# Check configuration
curl -X GET http://localhost:8001/config
```

#### Market Service Debug
```bash
# Check market data generation
curl -v -X GET http://localhost:8002/quote/AAPL

# Check caching behavior
curl -H "Cache-Control: no-cache" http://localhost:8002/quote/AAPL
```

#### Redis Debug
```bash
# Check Redis memory usage
docker exec trading-redis redis-cli info memory

# Monitor Redis commands
docker exec trading-redis redis-cli monitor

# Check cached data
docker exec trading-redis redis-cli keys "*"
```

---

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

#### 1. Services Not Starting

**Problem**: Services fail to start or timeout
```bash
# Check logs for specific error
docker-compose -f core-optimized.yml logs service-name

# Common solutions:
docker-compose -f core-optimized.yml down  # Stop all
docker system prune -f                     # Clean system
./fast-startup.sh clean                    # Full cleanup
./fast-startup.sh                          # Restart optimized
```

#### 2. Port Already in Use

**Problem**: `bind: address already in use`
```bash
# Find process using port
lsof -i :8001
lsof -i :8002
lsof -i :6379

# Kill process or change port in docker-compose
kill -9 <PID>
```

#### 3. Memory Issues

**Problem**: Services running out of memory
```bash
# Check memory usage
docker stats --no-stream

# Increase memory limits in core-optimized.yml
deploy:
  resources:
    limits:
      memory: 512M  # Increase from 256M
```

#### 4. Build Failures

**Problem**: Docker build fails
```bash
# Clear build cache
docker builder prune -f

# Rebuild without cache
docker-compose -f core-optimized.yml build --no-cache

# Check disk space
df -h
```

#### 5. Service Communication Issues

**Problem**: Services can't communicate
```bash
# Check network
docker network ls
docker network inspect microservices_trading-network

# Test connectivity
docker exec trading-market-service ping core-service
docker exec trading-market-service curl http://core-service:8001/health
```

### Debug Command Cheat Sheet

```bash
# Quick debug commands
alias docker-logs="docker-compose -f core-optimized.yml logs"
alias docker-ps="docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
alias docker-stats="docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'"

# Service health
alias health-check="curl -s http://localhost:8001/health && curl -s http://localhost:8002/health"

# Performance check
alias perf-check="./fast-startup.sh metrics"
```

---

## 📊 Performance Monitoring

### Real-time Monitoring

#### System Resources
```bash
# Container resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# System resource usage
top -p $(docker inspect -f '{{.State.Pid}}' trading-core-service)
```

#### Service Response Times
```bash
# Measure response times
time curl -s http://localhost:8001/health
time curl -s http://localhost:8002/quote/AAPL

# Continuous monitoring
watch -n 1 'curl -w "Time: %{time_total}s\n" -s -o /dev/null http://localhost:8001/health'
```

### Performance Benchmarking

#### Load Testing
```bash
# Simple load test with curl
for i in {1..100}; do
  curl -s http://localhost:8002/quote/AAPL > /dev/null &
done
wait

# Using Apache Bench (if installed)
ab -n 1000 -c 10 http://localhost:8001/health
ab -n 1000 -c 10 http://localhost:8002/quote/AAPL
```

#### Memory Profiling
```bash
# Memory usage over time
while true; do
  docker stats --no-stream --format "{{.Name}}: {{.MemUsage}}" | grep trading
  sleep 5
done
```

---

## 🎯 Advanced Testing Scenarios

### 1. Failure Testing

#### Service Failure Simulation
```bash
# Stop core service, test market service behavior
docker stop trading-core-service
curl -v http://localhost:8002/validate-and-quote

# Stop Redis, test caching fallback
docker stop trading-redis
curl -v http://localhost:8002/quote/AAPL
```

#### Network Partition Testing
```bash
# Disconnect service from network
docker network disconnect microservices_trading-network trading-core-service

# Test behavior and reconnect
docker network connect microservices_trading-network trading-core-service
```

### 2. Data Validation Testing

#### Invalid Data Testing
```bash
# Test invalid signal validation
curl -X POST http://localhost:8001/validate/signal \
  -H "Content-Type: application/json" \
  -d '{"symbol": "", "signal_type": "INVALID", "confidence": -1}'

# Test malformed requests
curl -X POST http://localhost:8002/quote \
  -H "Content-Type: application/json" \
  -d '{"malformed": json}'
```

### 3. Concurrency Testing

#### Concurrent Request Testing
```bash
# Test concurrent requests
for i in {1..50}; do
  curl -s http://localhost:8002/quote/AAPL &
  curl -s http://localhost:8001/health &
done
wait
```

### 4. Cache Testing

#### Redis Cache Validation
```bash
# Test cache hit/miss
curl -H "X-Debug: true" http://localhost:8002/quote/AAPL  # Miss
curl -H "X-Debug: true" http://localhost:8002/quote/AAPL  # Hit

# Check cache expiration
docker exec trading-redis redis-cli ttl "quote:AAPL"
```

---

## 📈 Testing Best Practices

### 1. Automated Testing Pipeline
```bash
# Complete test sequence
./fast-startup.sh clean     # Clean environment
./fast-startup.sh test      # Full test suite
./fast-startup.sh metrics   # Performance check
```

### 2. Testing Checklist

- [ ] Services start successfully
- [ ] Health checks pass
- [ ] Individual endpoints work
- [ ] Service communication works
- [ ] Error handling works
- [ ] Performance is acceptable
- [ ] Memory usage is reasonable
- [ ] Logs are clean

### 3. Performance Targets

- **Startup Time**: < 60 seconds (vs 5+ minutes previously)
- **Service Response**: < 100ms for health checks
- **API Response**: < 500ms for data endpoints  
- **Memory Usage**: < 256MB per service
- **CPU Usage**: < 50% per service

---

## 🛠️ Tools and Commands Summary

### Essential Commands
```bash
# Quick start optimized
./fast-startup.sh

# Full test suite
./fast-startup.sh test

# Individual service test
./test-scripts/test-service.sh <service-name>

# Integration test
./test-scripts/test-integration.sh

# Performance metrics
./fast-startup.sh metrics

# Clean restart
./fast-startup.sh clean
```

### Debugging Commands
```bash
# Logs
docker-compose -f core-optimized.yml logs -f

# Container status  
docker ps

# Resource usage
docker stats

# Network inspection
docker network inspect microservices_trading-network

# Service health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

---

## 🎯 Next Steps

After successful testing:

1. **Implement Phase 2 Services**: Portfolio and Order services
2. **Add Monitoring Dashboard**: Comprehensive service monitoring
3. **Implement CI/CD Pipeline**: Automated testing and deployment
4. **Add Security Features**: Authentication and authorization
5. **Scale Services**: Horizontal scaling and load balancing

---

*This comprehensive testing guide ensures reliable, fast, and debuggable microservices deployment! 🚀*
