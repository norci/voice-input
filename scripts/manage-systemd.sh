#!/usr/bin/env bash
set -euo pipefail

# Manage voice-input systemd user service
# Usage: ./manage-systemd.sh [install|uninstall]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="voice-input.service"
FUNASR_SERVICE_NAME="funasr-wss-server.service"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
FUNASR_SERVICE_FILE="${SYSTEMD_USER_DIR}/${FUNASR_SERVICE_NAME}"

usage() {
    echo "Usage: $0 {install|uninstall}"
    echo ""
    echo "Commands:"
    echo "  install    Install and enable the voice-input and funasr-wss-server systemd user services"
    echo "  uninstall  Stop, disable and remove the voice-input and funasr-wss-server systemd user services"
    exit 1
}

calculate_paths() {
    # Calculate project path relative to home directory
    RELATIVE_PROJECT_DIR="${PROJECT_DIR#$HOME/}"
    if [[ "${PROJECT_DIR}" == "${RELATIVE_PROJECT_DIR}" ]]; then
        echo "Warning: Project directory is not under home directory"
        echo "Service file will use absolute path: ${PROJECT_DIR}"
        PROJECT_PATH="${PROJECT_DIR}"
    else
        PROJECT_PATH="%h/${RELATIVE_PROJECT_DIR}"
    fi

    # Get uv path - try to use %h for user-installed locations
    UV_PATH="$(which uv)"
    if [[ "${UV_PATH}" == "${HOME}/.local/bin/uv" ]] || [[ "${UV_PATH}" == "${HOME}/.cargo/bin/uv" ]]; then
        UV_EXEC="%h${UV_PATH#$HOME}"
    else
        UV_EXEC="${UV_PATH}"
    fi
}

do_install() {
    echo "Installing voice-input systemd user service..."

    # Verify project directory structure
    if [[ ! -f "${PROJECT_DIR}/pyproject.toml" ]]; then
        echo "Error: Project directory not found or invalid"
        echo "Expected to find pyproject.toml in: ${PROJECT_DIR}"
        echo "Please run this script from the project's scripts/ directory"
        exit 1
    fi

    # Check if uv is available
    if ! command -v uv &> /dev/null; then
        echo "Error: uv is not installed or not in PATH"
        echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    calculate_paths

    # Create systemd user directory if it doesn't exist
    mkdir -p "${SYSTEMD_USER_DIR}"

    # Create the voice-input service file
    cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Voice Input - Chinese Voice Input Method based on FunASR
After=graphical-session.target funasr-wss-server.service
Wants=graphical-session.target funasr-wss-server.service
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=${UV_EXEC} --directory ${PROJECT_PATH} run voice-input
Restart=on-failure
RestartSec=5
WorkingDirectory=${PROJECT_PATH}

[Install]
WantedBy=graphical-session.target
EOF

    echo "Service file created at: ${SERVICE_FILE}"

    # Create the funasr-wss-server service file
    # Directly execute uv run instead of using the shell script
    cat > "${FUNASR_SERVICE_FILE}" << EOF
[Unit]
Description=FunASR WebSocket Server
Documentation=https://github.com/modelscope/FunASR
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=%u
WorkingDirectory=${PROJECT_PATH}
ExecStart=${UV_EXEC} --directory ${PROJECT_PATH}/FunASR/runtime/python/websocket run funasr_wss_server.py --host 127.0.0.1 --port 10095
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
EOF

    echo "FunASR service file created at: ${FUNASR_SERVICE_FILE}"

    # Reload systemd user daemon
    systemctl --user daemon-reload

    # Enable the voice-input service to start with graphical session
    systemctl --user enable "${SERVICE_NAME}"

    # Enable the funasr-wss-server service
    systemctl --user enable "${FUNASR_SERVICE_NAME}"

    echo ""
    echo "Installation complete!"
    echo ""
    echo "To start the service now:"
    echo "  systemctl --user start ${SERVICE_NAME}"
    echo ""
    echo "To check service status:"
    echo "  systemctl --user status ${SERVICE_NAME}"
    echo ""
    echo "To view logs:"
    echo "  journalctl --user -u ${SERVICE_NAME} -f"
    echo ""
    echo "To stop the service:"
    echo "  systemctl --user stop ${SERVICE_NAME}"
    echo ""
    echo "To disable the service:"
    echo "  systemctl --user disable ${SERVICE_NAME}"
    echo ""

    # Ask if user wants to start the services now
    read -p "Start the services now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting funasr-wss-server service..."
        systemctl --user start "${FUNASR_SERVICE_NAME}"
        sleep 2
        echo "Starting voice-input service..."
        systemctl --user start "${SERVICE_NAME}"
        echo "Services started. Checking status..."
        sleep 2
        echo "FunASR service status:"
        systemctl --user status "${FUNASR_SERVICE_NAME}" --no-pager
        echo ""
        echo "Voice-input service status:"
        systemctl --user status "${SERVICE_NAME}" --no-pager
    fi
}

do_uninstall() {
    echo "Uninstalling voice-input systemd user service..."

    # Check if voice-input service is installed
    if [[ ! -f "${SERVICE_FILE}" ]]; then
        echo "Service file not found at: ${SERVICE_FILE}"
        echo "Service may not be installed or already removed."
    else
        # Stop the service if it's running
        if systemctl --user is-active "${SERVICE_NAME}" &> /dev/null; then
            echo "Stopping voice-input service..."
            systemctl --user stop "${SERVICE_NAME}"
        fi

        # Disable the service
        if systemctl --user is-enabled "${SERVICE_NAME}" &> /dev/null; then
            echo "Disabling voice-input service..."
            systemctl --user disable "${SERVICE_NAME}"
        fi

        # Remove the service file
        echo "Removing voice-input service file..."
        rm -f "${SERVICE_FILE}"
    fi

    # Check if funasr-wss-server service is installed
    if [[ ! -f "${FUNASR_SERVICE_FILE}" ]]; then
        echo "FunASR service file not found at: ${FUNASR_SERVICE_FILE}"
        echo "FunASR service may not be installed or already removed."
    else
        # Stop the funasr service if it's running
        if systemctl --user is-active "${FUNASR_SERVICE_NAME}" &> /dev/null; then
            echo "Stopping funasr-wss-server service..."
            systemctl --user stop "${FUNASR_SERVICE_NAME}"
        fi

        # Disable the funasr service
        if systemctl --user is-enabled "${FUNASR_SERVICE_NAME}" &> /dev/null; then
            echo "Disabling funasr-wss-server service..."
            systemctl --user disable "${FUNASR_SERVICE_NAME}"
        fi

        # Remove the funasr service file
        echo "Removing funasr-wss-server service file..."
        rm -f "${FUNASR_SERVICE_FILE}"
    fi

    # Reload systemd user daemon
    systemctl --user daemon-reload

    echo ""
    echo "Uninstallation complete!"
    echo "The voice-input and funasr-wss-server services have been removed."
}

# Main
if [[ $# -ne 1 ]]; then
    usage
fi

case "$1" in
    install)
        do_install
        ;;
    uninstall)
        do_uninstall
        ;;
    *)
        echo "Error: Unknown command '$1'"
        usage
        ;;
esac
