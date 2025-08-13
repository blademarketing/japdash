# JAP Dashboard

A comprehensive social media automation platform that integrates with Just Another Panel (JAP) API and RSS.app to provide automated RSS-triggered social media growth services.

## 🎯 Features

- **📱 Multi-Platform**: Instagram, Facebook, X (Twitter), TikTok
- **📸 Screenshot Automation**: Before/after screenshots for every order
- **🤖 AI Comments**: Automated comment generation using LLM
- **📡 RSS Automation**: Auto-execute actions on new posts  
- **⚡ Instant Execution**: On-demand service execution
- **📊 Complete Tracking**: Full execution history and monitoring
- **🏷️ Smart Organization**: Tag-based account management

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd japdash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure and run
cp .env.example .env
# Edit .env with your API keys
python app.py
```

Access dashboard at **http://localhost:5079** (default: admin/admin)

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Getting Started](docs/guides/getting-started.md)** - Complete setup and development guide
- **[API Reference](docs/api/endpoints.md)** - REST API endpoints documentation  
- **[System Architecture](docs/architecture/system-overview.md)** - Technical architecture overview
- **[Database Schema](docs/database-schema.md)** - Complete database documentation
- **[UI Design Guide](docs/ui/design-guide.md)** - Frontend development patterns
- **[User Workflows](docs/ui/user-workflows.md)** - User interaction patterns

## 🔧 Technology Stack

- **Backend**: Python Flask with SQLite
- **Frontend**: Vanilla JavaScript with Tailwind CSS
- **External APIs**: JAP API, RSS.app API, Flowise LLM, GoLogin Screenshots
- **Database**: SQLite with automatic migrations

## 📋 Requirements

- Python 3.8+
- JAP API key ([justanotherpanel.com](https://justanotherpanel.com))
- RSS.app API key ([rss.app](https://rss.app))
- GoLogin API key and profiles (for screenshots)
- Screenshot service API key (gologin.electric-marinade.com)
- Flowise URL (optional, for AI comments)

## 🤝 Contributing

1. Read the [Getting Started Guide](docs/guides/getting-started.md)
2. Follow development patterns in the documentation
3. Test thoroughly before submitting changes
4. Update documentation for new features

## 📄 License

Private and proprietary to Blade Marketing.

---

For detailed information, see the [complete documentation](docs/README.md).