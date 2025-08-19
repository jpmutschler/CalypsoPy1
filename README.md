# CalypsoPy

[![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)](https://github.com/your-username/CalypsoPy)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Beta-orange.svg)](https://github.com/your-username/CalypsoPy)

> A modern GUI application for serial communication with the Gen6 PCIe Atlas 3 Host Card from Serial Cables

## 🚀 Overview

CalypsoPy is a professional serial communication interface designed specifically for the Gen6 PCIe Atlas 3 Host Card from Serial Cables. It provides a modern, intuitive GUI for device management, monitoring, and configuration with advanced features like intelligent response handling, data caching, and comprehensive debugging tools.

### ✨ Key Features

- **Advanced Response Handling**: Intelligent fragmented response collection and processing
- **Real-time Monitoring**: Live device status, thermal monitoring, and performance metrics
- **Data Caching**: Persistent data storage with automatic refresh capabilities
- **Demo Mode**: Complete training environment with simulated device responses
- **Modern UI**: Clean, responsive interface with multiple dashboard views
- **Enterprise-grade**: Robust error handling, logging, and debugging capabilities
- **Modular Architecture**: Well-organized codebase with Admin and Dashboard modules

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Features](#features)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

## 💻 Installation

### Prerequisites

- Python 3.8 or higher
- Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- Serial port access (for real device communication)

### Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `pyserial>=3.5`
- `tkinter` (usually included with Python)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/CalypsoPy.git
   cd CalypsoPy
   ```

2. **Install dependencies:**
   ```bash
   pip install pyserial
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

## 🚀 Quick Start

### Demo Mode (No Hardware Required)

1. Launch CalypsoPy: `python main.py`
2. Check "🎭 Demo Mode" in the connection window
3. Click "Connect to Device"
4. Explore all features with simulated data

### Real Device Connection

1. Connect your Gen6 PCIe Atlas 3 Host Card via serial
2. Launch CalypsoPy: `python main.py`
3. Select your COM port from the dropdown
4. Click "Connect to Device"
5. Navigate through the dashboard tabs

## 🎯 Features

### 📊 Dashboard Components

| Dashboard | Description | Key Features |
|-----------|-------------|--------------|
| **Host Card Information** | Device status and specifications | Serial number, firmware version, thermal data |
| **Link Status** | Connection and port monitoring | Port speeds, link states, golden finger status |
| **Port Configuration** | Port settings and control | Individual port management |
| **Compliance** | Standards compliance testing | USB 3.0, EMI/EMC validation |
| **Registers** | Direct register access | Read/write register operations |
| **Advanced** | System administration | Command interface, cache management, debug tools |
| **Resets** | Device reset operations | Soft, hard, factory, and link resets |
| **Firmware Updates** | Firmware management | Update checking and installation |
| **Help** | Documentation and support | User guides, command reference, logs |

### 🔧 Advanced Features

#### Response Handler
- **Intelligent Collection**: Automatically assembles fragmented device responses
- **Pattern Recognition**: Understands different command response formats
- **Quality Validation**: Ensures response completeness before processing
- **Timeout Management**: Graceful handling of communication timeouts

#### Data Caching
- **Persistent Storage**: JSON-based data persistence between sessions
- **Automatic Refresh**: Configurable refresh intervals for live data
- **Cache Management**: Manual cache control and cleanup tools
- **Performance Optimization**: Reduces device communication overhead

#### Debug System
- **Centralized Control**: Single-point debug enable/disable
- **Categorized Logging**: Granular control over debug message types
- **Runtime Control**: Toggle debug modes from the application UI
- **Performance Aware**: Debug operations only execute when enabled

### ⚙️ Settings Management

#### UI Settings
- **Theme Control**: Dark/light theme selection
- **Window Management**: Size, position, and layout preferences
- **Font Configuration**: Family and size customization

#### Communication Settings
- **Serial Parameters**: Baud rate, timeout, retry configuration
- **Logging Levels**: Configurable logging verbosity
- **Command History**: Persistent command history management

#### Cache Settings
- **Storage Options**: Cache directory and size limits
- **TTL Configuration**: Time-to-live settings for cached data
- **Cleanup Policies**: Automatic cache maintenance

## 📁 Project Structure

```
CalypsoPy/
├── main.py                          # Application entry point
├── README.md                        # Project documentation
├── requirements.txt                 # Python dependencies
├── LICENSE                          # License information
│
├── Admin/                           # Administrative modules
│   ├── __init__.py                  # Admin module initialization
│   ├── advanced_response_handler.py # Fragmented response processing
│   ├── cache_manager.py             # Data caching and persistence
│   ├── debug_config.py              # Centralized debug control
│   ├── enhanced_sysinfo_parser.py   # System information parsing
│   ├── settings_manager.py          # Application settings management
│   └── settings_ui.py               # Settings interface components
│
├── Dashboards/                      # Dashboard components
│   ├── __init__.py                  # Dashboard module initialization
│   ├── demo_mode_integration.py     # Demo mode simulation
│   └── host_card_info.py            # Host card information dashboard
│
├── DemoData/                        # Demo mode data files
│   └── sysinfo.txt                  # Sample system information
│
├── assets/                          # Application assets
│   └── Logo_gal_ico.ico             # Application icon
│
└── docs/                            # Documentation (optional)
    ├── API.md                       # API documentation
    ├── CONFIGURATION.md             # Configuration guide
    └── TROUBLESHOOTING.md           # Troubleshooting guide
```

## ⚙️ Configuration

### Debug Configuration

Edit `Admin/debug_config.py` to control debug output:

```python
# Main debug control - Change this line to enable/disable ALL debug
DEBUG_ENABLED = True  # Set to False to disable debug messages

# Category-specific controls
DEBUG_CATEGORIES = {
    'response_handler': True,    # Response processing debug
    'cache_manager': True,       # Cache operations debug
    'serial_cli': True,          # Serial communication debug
    # ... additional categories
}
```

### Settings Configuration

Access settings through:
- **UI**: Click the gear icon (⚙️) in the connection window or dashboard
- **File**: Settings are stored in your user's application data directory
- **Runtime**: Modify settings through the Advanced dashboard

## 📖 Usage

### Basic Operation

1. **Connection**: Select demo mode or real device connection
2. **Navigation**: Use the sidebar to switch between dashboards
3. **Monitoring**: View real-time device status and performance
4. **Configuration**: Modify settings through the gear icon
5. **Debugging**: Use Advanced dashboard for troubleshooting

### Command Interface

Access the direct command interface through the Advanced dashboard:

```
Available Commands:
- help          Show available commands
- status        Get device status  
- version       Get firmware version
- sysinfo       Get complete system information
- ver           Get detailed version info
- lsd           Get system diagnostics
- reset         Reset device
- showport      Check port status
```

### Demo Mode Features

Demo mode provides:
- **Full Functionality**: All features work with simulated data
- **Training Environment**: Safe space to learn the interface
- **Realistic Responses**: Actual device response simulation
- **No Hardware Required**: Perfect for development and testing

## 🛠 Development

### Development Setup

1. **Clone the repository**
2. **Create virtual environment:**
   ```bash
   python -m venv calypsopy-env
   source calypsopy-env/bin/activate  # Linux/macOS
   calypsopy-env\Scripts\activate     # Windows
   ```
3. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

### Code Organization

- **Admin Module**: System administration, caching, parsing, settings
- **Dashboards Module**: UI components and dashboard implementations
- **Main Application**: Entry point, connection management, core UI

### Adding New Features

#### New Dashboard
1. Create dashboard file in `Dashboards/`
2. Update `Dashboards/__init__.py`
3. Add dashboard tile in `main.py`
4. Implement dashboard content method

#### New Admin Tool
1. Create tool file in `Admin/`
2. Update `Admin/__init__.py`
3. Add tool to Advanced dashboard
4. Implement tool functionality

### Debug System

Use the centralized debug system for development:

```python
from Admin.debug_config import debug_print, debug_error

# Category-specific debugging
debug_print("Response received", 'response_handler')
debug_error("Connection failed", 'serial_cli')

# Conditional expensive operations
if is_debug_enabled('cache_manager'):
    debug_print(f"Cache details: {expensive_operation()}", 'cache_manager')
```

## 🐛 Troubleshooting

### Common Issues

#### Connection Problems
- **Check COM port**: Ensure correct port selection
- **Driver Issues**: Verify device drivers are installed
- **Port Conflicts**: Close other applications using the port
- **Demo Mode**: Use demo mode to test without hardware

#### Performance Issues
- **Cache Problems**: Clear cache through Advanced dashboard
- **Debug Overhead**: Disable debug in `Admin/debug_config.py`
- **Memory Usage**: Monitor through Advanced dashboard statistics

#### UI Issues
- **Display Problems**: Check display scaling and resolution
- **Theme Issues**: Switch themes in settings
- **Window Problems**: Reset window position in settings

### Debug Information

Enable debug mode for detailed troubleshooting:
1. Edit `Admin/debug_config.py`
2. Set `DEBUG_ENABLED = True`
3. Run application and reproduce issue
4. Check console output for debug messages

### Log Files

Export session logs through the Help dashboard for support requests.

## 🤝 Contributing

### Development Guidelines

1. **Code Style**: Follow PEP 8 conventions
2. **Documentation**: Update docstrings and comments
3. **Testing**: Test both demo and real device modes
4. **Debug**: Use centralized debug system
5. **Modular Design**: Keep Admin and Dashboard separation

### Submitting Changes

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

## 📝 Changelog

### Beta 1.1.0 (2024-12-09)
- ✅ Added Advanced Fragmented Response Handler
- ✅ Implemented data caching with JSON persistence
- ✅ Created environment settings management
- ✅ Added auto-refresh capabilities
- ✅ Built settings UI with configuration controls
- ✅ Organized code structure with Admin and Dashboard modules
- ✅ Added centralized debug system
- ✅ Optimized dashboard performance

### Beta 1.0.0 (2024-12-08)
- ✅ Initial beta release
- ✅ Basic serial communication
- ✅ Host card information dashboard
- ✅ Demo mode implementation
- ✅ Modern GUI interface

## 📄 License

This project is proprietary software developed by Serial Cables, LLC.

© 2025 Serial Cables, LLC. All rights reserved.

---

## 📞 Support

- **Documentation**: See `docs/` directory for detailed guides
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Support**: Contact Serial Cables support team
- **Community**: Join the Serial Cables developer community

## 🙏 Acknowledgments

- **Serial Cables Team**: Core development and hardware integration
- **Python Community**: Libraries and frameworks
- **Beta Testers**: Early feedback and testing

---

**Made with ❤️ by the Serial Cables Development Team**