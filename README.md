# Time Economy - Cybernetic Labor Market

A web application for implementing a time-based economy in small communities (5-10 people), based on the principles of timebanking, cybernetic governance (Viable System Model), and platform cooperativism.

## Core Principles

- **1 Hour = 1 Credit**: All human time is valued equally
- **Mutual Credit**: Non-circulating time credits, no fiat conversion
- **Transparent Governance**: Community-driven decisions with full transparency
- **Algedonic Signals**: Automatic alerts when members approach credit/deficit limits

## Features

- **Member Directory**: Manage community members with skill inventories
- **Transaction Logging**: Record time credit exchanges with status tracking
- **Balance Dashboard**: Real-time view of all member balances with visual indicators
- **Needs Board**: Post and fulfill community service requests
- **Governance Log**: Track decisions, votes, and meeting notes
- **Skills Matching**: Automatic identification of skill/want matches
- **System Health Metrics**: Monitor liquidity, velocity, and circulation

## Screenshots

### Dashboard
![Dashboard](screenshots/01_dashboard.png)

### Members
![Members](screenshots/02_members.png)

### Member Detail
![Member Detail](screenshots/03_member_detail.png)

### Transactions
![Transactions](screenshots/04_transactions.png)

### Needs & Offers
![Needs](screenshots/05_needs.png)

### Skills Directory
![Skills](screenshots/06_skills.png)

### Governance Log
![Governance](screenshots/07_governance.png)

## Quick Start

### Option 1: Docker (Recommended)

```bash
cd time_econ_app
docker-compose up -d
```

The app will be available at `http://localhost:8000`

### Option 2: Local Python

```bash
cd time_econ_app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The app will be available at `http://localhost:8000`

## System Architecture (VSM)

The application implements Stafford Beer's Viable System Model:

- **System 1 (Operations)**: Individual members self-scheduling and exchanging
- **System 2 (Coordination)**: Transaction logging, conflict resolution protocols
- **System 3 (Control)**: Real-time balance monitoring, credit caps (20/-10)
- **System 4 (Intelligence)**: Dashboard metrics, skill gap analysis
- **System 5 (Policy)**: Governance log with voting mechanisms

## Economic Mechanisms

- **Egalitarian Valuation**: All services valued at 1 hour = 1 credit
- **Initial Credit**: New members receive 5 credits to get started
- **Soft Limits**: 
  - Credit cap at 20 (hoarding alert)
  - Deficit limit at -10 (community check-in)
- **Social Demurrage**: Community encouragement to spend credits rather than hoard

## First Steps

1. Add your community members via the Members page
2. Have each member list their skills and wants
3. Start logging transactions when services are exchanged
4. Monitor the dashboard for system health and algedonic signals
5. Use the Governance log for community decisions

## Data Storage

All data is stored in a local SQLite database (`time_economy.db`). Back up this file regularly.

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite (via SQLAlchemy)
- **Frontend**: Jinja2 templates with Tailwind CSS
- **Charts**: Chart.js

## License

MIT License - Use freely for your community.
