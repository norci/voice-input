#!/usr/bin/env bash
set -euo pipefail

# Manage voice-input systemd user service
# Usage: ./manage-systemd.sh [install|uninstall]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="voice-input.service"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SYSTEMD_USER_DIR}/${SERVICE_NAME}"

usage() {
    echo "Usage: $0 {install|uninstall}"
    echo ""
    echo "Commands:"
    echo "  install    Install and enable the voice-input systemd user service"
    echo "  uninstall  Stop, disable and remove the voice-input systemd user service"
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

    # Create the service file
    cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Voice Input - Chinese Voice Input Method based on FunASR
After=graphical-session.target
Wants=graphical-session.target
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

    # Reload systemd user daemon
    systemctl --user daemon-reload

    # Enable the service to start with graphical session
    systemctl --user enable "${SERVICE_NAME}"

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

    # Ask if user wants to start the service now
    read -p "Start the service now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl --user start "${SERVICE_NAME}"
        echo "Service started. Checking status..."
        sleep 2
        systemctl --user status "${SERVICE_NAME}" --no-pager
    fi
}

do_uninstall() {
    echo "Uninstalling voice-input systemd user service..."

    # Check if service is installed
    if [[ ! -f "${SERVICE_FILE}" ]]; then
        echo "Service file not found at: ${SERVICE_FILE}"
        echo "Service may not be installed or already removed."
        exit 0
    fi

    # Stop the service if it's running
    if systemctl --user is-active "${SERVICE_NAME}" &> /dev/null; then
        echo "Stopping service..."
        systemctl --user stop "${SERVICE_NAME}"
    fi

    # Disable the service
    if systemctl --user is-enabled "${SERVICE_NAME}" &> /dev/null; then
        echo "Disabling service..."
        systemctl --user disable "${SERVICE_NAME}"
    fi

    # Remove the service file
    echo "Removing service file..."
    rm -f "${SERVICE_FILE}"

    # Reload systemd user daemon
    systemctl --user daemon-reload

    echo ""
    echo "Uninstallation complete!"
    echo "The voice-input service has been removed."
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
