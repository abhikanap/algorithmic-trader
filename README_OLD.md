# 🚀 Algorithmic Trading Platform

A comprehensive, production-ready algorithmic trading platform built with Python, featuring advanced portfolio management, risk controls, backtesting, and real-time monitoring capabilities.

## 🚀 Features

- **Multi-Phase Pipeline**: Screener → Analyzer → Strategy → Execution → Backtesting
- **Pattern Recognition**: Advanced intraday and multi-day pattern classification
- **Capital Allocation**: Intelligent bucket-based position sizing
- **Time Segmentation**: Market-hours-aware trade scheduling
- **Risk Management**: Built-in volatility and position size controls
- **Cloud-Native**: Kubernetes-ready with AWS EKS deployment
- **Comprehensive Testing**: Full test coverage with pytest

## 📋 Architecture

### Phase 1: Screener
- **Yahoo Finance Integration**: Real-time market data with rate limiting
- **Feature Engineering**: ATR, RSI, volume, gap analysis
- **Filtering Engine**: Configurable criteria for symbol selection
- **Ranking System**: Multi-factor scoring for symbol prioritization

### Phase 2: Analyzer
- **Intraday Patterns**: Morning spike/fade, surge/uptrend, plunge/recovery, selloff/downtrend, choppy/range
- **Multi-day Patterns**: Sustained trends, blowoff tops, reversals, consolidation
- **Confidence Scoring**: Machine learning-inspired pattern confidence
- **Strategy Hints**: Bucket and time slot recommendations

### Phase 3: Strategy Engine
- **Capital Buckets**: 5 specialized allocation buckets (A-E)
  - **A**: Penny stocks & microcap movers (15%)
  - **B**: Large-cap intraday trends (35%)
  - **C**: Multi-day swing trades (30%)
  - **D**: Catalyst-driven movers (15%)
  - **E**: Defensive hedges (5%)
- **Position Sizing**: Volatility-adjusted with confidence weighting
- **Time Segments**: Market open, late morning, midday, afternoon, close

## 🛠️ Installation

### Quick Start with Docker (Recommended)

#### Prerequisites
- Docker Desktop or Docker Engine
- Docker Compose
- Git

#### Docker Setup
```bash
# Clone the repository
git clone <repository-url>
cd algorithmic-trader

# Set up Docker environment
./docker-setup.sh setup

# Run tests to verify everything works
./docker-test.sh

# Access the dashboard
open http://localhost:8501
```

#### Running the Trading Pipeline
```bash
# Run the full trading pipeline
./docker-setup.sh pipeline

# Run backtesting
./docker-setup.sh backtest

# Stop all services
./docker-setup.sh stop

# View logs
./docker-setup.sh logs
```

### Manual Installation (Advanced)

#### Prerequisites
- Python 3.11+
- Virtual environment tool (venv or conda)
- Redis server
- PostgreSQL database
- Git

#### Setup
```bash
# Clone the repository
git clone <repository-url>
cd algorithmic-trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize system
python main.py init

# Check status
python main.py status
```

## 🚦 Usage

### Full Pipeline
Run the complete trading pipeline for today:
```bash
python main.py pipeline
```

Run for specific date with custom capital:
```bash
python main.py pipeline --date 2024-01-15 --capital 100000
```

### Individual Components

#### Screener
```bash
# Run screener for today
python main.py screener run

# Run with custom symbols
python main.py screener run --symbols AAPL,MSFT,GOOGL

# Show screener results
python main.py screener report --date 2024-01-15
```

#### Analyzer
```bash
# Run analyzer (requires screener data)
python main.py analyzer run

# List available patterns
python main.py analyzer patterns

# Generate analysis report
python main.py analyzer report --date 2024-01-15
```

#### Strategy
```bash
# Run strategy allocation
python main.py strategy allocate

# Show bucket configurations
python main.py strategy buckets

# View trade signals
python main.py strategy signals --date 2024-01-15 --top 10
```

## 📊 Data Flow

```
Market Data → Screener → Analyzer → Strategy → Execution
     ↑           ↓          ↓          ↓         ↓
   Yahoo      Features   Patterns   Signals   Orders
  Finance    (ATR,RSI)  (Morning   (Bucket   (Alpaca
             Filtering   Spike)     Alloc)     API)
```  
- **Execute**: Place trades via **Alpaca API** (live or paper trading), with intraday portfolio rebalancing.  
- **Validate**: Backtest strategies using **QuantConnect Lean engine** across historical intraday and multi-day data.  
- **Deploy**: Scale using **AWS EKS**, with observability, CI/CD automation, and modular services.  
- **Evolve**: Incorporate **AI/LLMs** for adaptive decision-making and **VLMs** for chart-based pattern recognition.  

---

## 🔑 Core Principles
- **Pattern-Driven**: Recognize and exploit repeatable intraday/multi-day patterns.  
- **Capital Buckets**: Allocate risk capital across distinct categories (penny movers, large-cap trends, etc.).  
- **Time Segments**: Strategies shift by intraday phase (open, midday, afternoon, power hour).  
- **Risk Discipline**: ATR-based stops, strict position sizing, daily loss limits.  
- **AI-Enhanced**: LLMs for sentiment/news flow, VLMs for chart recognition, RL for adaptive allocations.  
- **Cloud-Native**: Services run on AWS EKS with Kubernetes scaling, logs in CloudWatch, data in S3/RDS.  

---

## 🏗️ System Architecture

+––––––––+       +––––––––+       +––––––––+
|  Data Sources  | —>  |    Screener    | —>  |    Analyzer    |
+––––––––+       +––––––––+       +––––––––+
|                           |                         |
v                           v                         v
Yahoo, TradingView       Volatility filters        Intraday/Multi-day
QuantConnect Data        Dollar Vol, ATR%          Pattern classification

+––––––––+       +––––––––+       +––––––––+
| Strategy Engine| —>  |   Execution    | —>  |   Backtesting  |
+––––––––+       +––––––––+       +––––––––+
Buckets + Timeslots   Orders via Alpaca API    QuantConnect Lean
Capital allocation    Portfolio rebalancing    Walk-forward validation

+––––––––+       +––––––––+
|  AWS EKS Infra | —>  | Dashboards/Logs|
+––––––––+       +––––––––+
S3, RDS, CloudWatch   Streamlit/FastAPI UI

---

## 📊 Trading Concepts

### 🔄 Intraday Patterns
- **Morning Spike → Fade** (Pump & Fade)  
- **Morning Surge → All-Day Uptrend** (Trend-Up Day)  
- **Morning Plunge → Midday Recovery** (Intraday Reversal)  
- **Morning Sell-Off → All-Day Downtrend** (Trend-Down Day)  
- **Choppy/Range-Bound Day** (Sideways/Whipsaw)  

### 📈 Multi-Day Patterns
- **Sustained Uptrend (Multi-Day Rally)**  
- **Sustained Downtrend (Multi-Day Selloff)**  
- **Blow-Off Top / First Red Day**  
- **Downtrend → Reversal Up**  
- **Sideways Consolidation/Base**  

### 💰 Capital Buckets
- **Bucket A (20%)** – Penny stocks & microcap movers.  
- **Bucket B (30%)** – Large-cap intraday trend stocks.  
- **Bucket C (20%)** – Multi-day swing trades.  
- **Bucket D (20%)** – Catalyst-driven “market movers” (earnings, news).  
- **Bucket E (10%)** – Defensive hedges (ETFs, dividend plays).  

### ⏰ Time Segments
- **9:30–10:30 AM** – High volatility, spikes, gap plays.  
- **10:30–1:30 PM** – Midday consolidation, mean reversion.  
- **1:30–3:00 PM** – Reversals and continuation setups.  
- **3:00–4:00 PM** – Power Hour, institutional flows, closing imbalances.  

---

## 🛠️ Tool Stack
- **Broker/Execution**: Alpaca API (REST + WS, live & paper trading).  
- **Backtesting/Research**: QuantConnect Lean engine.  
- **Data Providers**: Yahoo Finance (`yfinance`), optional TradingView libraries, QuantConnect datasets.  
- **Infra**: AWS EKS (services as pods), S3 (artifacts), RDS (Postgres), CloudWatch (logs).  
- **Orchestration**: GitHub Actions CI/CD → Helm charts → EKS rollout.  
- **Frontend**: Streamlit or FastAPI dashboards.  
- **Language**: Python 3.11+, modular provider/strategy packages.  

---

## 📂 Documentation Map

This repo is **documentation-driven**. Each module has its own README for clarity and implementation guidance.

- [📖 Strategy Playbook](strategy/README_STRATEGY.md)  
  → Defines intraday & multi-day strategies, capital buckets, and time segments.  
  **Note:** The `strategy/` folder also contains **reference docs** derived from research notes (PDFs/MD), including:  
  - `Intraday Patterns.md`  
  - `Day Trading Strategy by Intraday Time Segments and Capital Buckets.pdf`  
  - `Comprehensive Classification of Stock Movement Patterns and Trading Strategies.pdf`  

- [🗺️ Planning Roadmap](planning/README_PLANNING.md)  
  → Phase-by-phase development plan: Screener → Analyzer → Strategy Engine → Execution → Backtesting → Deployment → AI/LLM integration.  

- [🧩 System Design](design/README_DESIGN.md)  
  → Detailed architecture, AWS EKS infra setup, provider abstraction, execution pipelines.  

- [⚡ Execution Guide](execution/README_EXECUTION.md)  
  → Order flow via Alpaca API, intraday rebalancing, trade tagging by bucket & timeslot.  

- [🧪 Testing Plan](testing/README_TESTING.md)  
  → Unit, integration, backtesting, and walk-forward validation framework.  

- [🔗 Integration Guide](integration/README_INTEGRATION.md)  
  → Alpaca integration, QuantConnect Lean setup, AWS EKS deployment pipelines, dashboards.  

- [🌱 Future Ideation](future/README_IDEATION.md)  
  → AI/LLM-driven decision-making, VLM chart recognition, reinforcement learning allocation agents.  

---

## 🚦 Development Status
- ✅ Screener: volatility & liquidity filters with artifacts (Parquet, JSONL, Markdown reports).  
- 🟡 Analyzer: pattern classifier in progress.  
- ⏳ Strategy Engine: bucket allocation logic to be added.  
- ⏳ Execution Engine: Alpaca integration (sandbox first).  
- ⏳ Backtesting: QuantConnect Lean integration.  
- ⏳ Deployment: AWS EKS rollout with CI/CD.  

---

## 🐳 Docker Deployment

The platform is fully containerized and can be deployed using Docker with a single command:

```bash
# Complete setup and deployment
./docker-setup.sh setup

# Test the deployment
./docker-test.sh

# Access the dashboard
open http://localhost:8501
```

### Docker Services
- **trading-engine**: Core trading logic and CLI
- **dashboard**: Streamlit web interface (port 8501)
- **postgres**: Database for trade data and analytics
- **redis**: Caching and session storage
- **pipeline-runner**: Automated trading pipeline execution
- **backtest-runner**: Historical backtesting service
- **prometheus**: Metrics collection (port 9090)
- **grafana**: Monitoring dashboard (port 3000)

### Docker Commands
```bash
# Start all services
./docker-setup.sh start

# Stop all services
./docker-setup.sh stop

# View service logs
./docker-setup.sh logs [service-name]

# Shell access to trading engine
./docker-setup.sh shell

# Run trading pipeline
./docker-setup.sh pipeline

# Run backtesting
./docker-setup.sh backtest

# View service status
./docker-setup.sh status
```

For detailed Docker documentation, see [DOCKER_GUIDE.md](DOCKER_GUIDE.md).

## ▶️ Quick Start

### With Docker (Recommended)
```bash
# Clone repo
git clone https://github.com/your-org/algorithmic-trader.git
cd algorithmic-trader

# Deploy with Docker
./docker-setup.sh setup
./docker-test.sh

# Access dashboard at http://localhost:8501
```

### Manual Setup
```bash
# Setup environment
cp config/.env.example .env
poetry install   # or uv sync

# Run screener
make screener.run

# Run analyzer (stub mode)
make analyzer.run

# Deploy to EKS
make deploy.eks


⸻

📜 Key Configuration
	•	.env → Alpaca keys, DB creds, feature flags.
	•	config/screener.yaml → Screener thresholds (ATR, HV, dollar volume).
	•	config/strategy.yaml → Bucket definitions, capital splits, time slot rules.
	•	infra/eks-values.yaml → Helm values for EKS deployment.

⸻

⚠️ Disclaimer

This repository is for research and educational purposes only.
Trading involves substantial risk. Always begin with paper trading.
Ensure compliance with Alpaca, QuantConnect, Yahoo, and TradingView terms of service.

⸻
