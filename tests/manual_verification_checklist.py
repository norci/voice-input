#!/usr/bin/env python3
"""Manual Verification Checklist for Story 4-3.

This script provides a checklist for manual testing of the voice-input application.
It cannot be fully automated because it requires:
- X11/Wayland display server
- Audio input device (microphone)
- Active D-Bus session
- FunASR server running
- Text injection target application

Usage:
    python tests/manual_verification_checklist.py

The script will print out the verification steps for each AC.
"""

import subprocess
import sys


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def print_checklist(title: str, items: list[str]) -> None:
    """Print a checklist with items."""
    print(f"\n{title}")
    print("-" * 40)
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item}")


def check_prerequisites() -> bool:
    """Check if prerequisites are available."""
    print_header("Prerequisites Check")

    checks = [
        ("Python 3.11+", sys.version_info >= (3, 11)),
        ("X11/Wayland", run_command("echo $DISPLAY") or run_command("echo $WAYLAND_DISPLAY")),
        ("Audio device", run_command("pactl list short sources")),
    ]

    all_ok = True
    for name, result in checks:
        status = "OK" if result else "MISSING"
        print(f"  {name}: {status}")
        if not result:
            all_ok = False

    return all_ok


def run_command(cmd: str) -> bool:
    """Run a shell command and return True if successful."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.returncode == 0


def get_command_output(cmd: str) -> str:
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def check_ac1_gui_startup() -> None:
    """Verification steps for AC1: GUI Normal Startup."""
    print_header("AC1: GUI Normal Startup")

    items = [
        "Start the application: voice-input",
        "Verify GUI window appears on screen",
        "Check window transparency (should be ~50% opaque)",
        "Verify window position (should be top-right corner)",
        "Check 'Start Recognition' button is visible",
        "Check 'Exit' button is visible",
        "Check status label shows 'Status: Idle' (状态: 空闲)",
        "Verify Socket service is ready (socket file created in XDG_RUNTIME_DIR)",
    ]
    print_checklist("Verification Steps:", items)


def check_ac2_recording() -> None:
    """Verification steps for AC2: Recording Function."""
    print_header("AC2: Click 'Start Recognition' to Record")

    items = [
        "Click 'Start Recognition' button",
        "Verify status changes to 'Status: Recording...' (状态: 录音中...)",
        "Verify button text changes to 'Stop Recognition' (停止识别)",
        "Speak into the microphone",
        "Verify audio is being captured (no errors in log)",
        "Click 'Stop Recognition' button",
        "Verify status returns to 'Status: Idle' (状态: 空闲)",
        "Verify button text returns to 'Start Recognition' (开始识别)",
    ]
    print_checklist("Verification Steps:", items)


def check_ac3_recognition_display() -> None:
    """Verification steps for AC3: Recognition Result Real-time Display."""
    print_header("AC3: Recognition Result Real-time Display")

    items = [
        "Click 'Start Recognition' button",
        "Speak a test phrase in Chinese",
        "Verify interim results appear in real-time (< 500ms delay)",
        "Verify status shows 'Recognizing...' (识别中...)",
        "Wait for final result",
        "Verify final result is displayed clearly",
    ]
    print_checklist("Verification Steps:", items)


def check_ac4_text_injection() -> None:
    """Verification steps for AC4: Final Result Injection."""
    print_header("AC4: Final Result Injection Success")

    items = [
        "Open a text editor (e.g., gedit, kate, or terminal)",
        "Click in the text input area to focus",
        "Click 'Start Recognition' button",
        "Speak a test phrase",
        "Wait for final result",
        "Verify text is injected into the focused application",
        "Verify display area clears after injection",
        "Verify status returns to 'Idle' (空闲)",
    ]
    print_checklist("Verification Steps:", items)


def check_ac5_socket_signals() -> None:
    """Verification steps for AC5: Unix Socket Signal Trigger."""
    print_header("AC5: Socket Signal Trigger Normal")

    items = [
        "Make sure voice-input is running",
        "Test Toggle via Socket:",
        "  echo 'toggle' | nc -U $XDG_RUNTIME_DIR/voice-input.sock",
        "Verify recording starts",
        "Run Toggle command again",
        "Verify recording stops",
        "Test Quit via Socket:",
        "  echo 'quit' | nc -U $XDG_RUNTIME_DIR/voice-input.sock",
        "Verify application exits",
    ]
    print_checklist("Verification Steps:", items)


def check_ac6_stability() -> None:
    """Verification steps for AC6: 30-minute Stability."""
    print_header("AC6: 30-minute Stability Test")

    items = [
        "Start the application",
        "Start recording",
        "Every 5 minutes, do a short voice input",
        "Monitor memory usage: ps -p $(pgrep -f voice-input) -o rss",
        "Monitor CPU usage: ps -p $(pgrep -f voice-input) -o pcpu",
        "Check /tmp/voice_gui.log for errors",
        "After 30 minutes, verify no crashes",
        "Verify memory usage is stable (no significant growth)",
        "Verify CPU usage is normal (< 20%)",
    ]
    print_checklist("Verification Steps:", items)


def main() -> int:
    """Main function."""
    print("=" * 60)
    print("  Voice-Input Manual Verification Checklist")
    print("  Story 4-3: Manual Function Verification")
    print("=" * 60)

    # Check prerequisites
    if not check_prerequisites():
        print("\nWARNING: Some prerequisites are missing!")
        print("Some checks may not work properly.")

    # AC verification sections
    check_ac1_gui_startup()
    check_ac2_recording()
    check_ac3_recognition_display()
    check_ac4_text_injection()
    check_ac5_socket_signals()
    check_ac6_stability()

    # Summary
    print_header("Summary")
    print(
        """
After completing all verification steps, mark them as passed
in the story file: _bmad-output/implementation-artifacts/4-3-manual-verification.md

The automated tests in tests/integration/test_full_flow_e2e.py
verify the module integration without requiring hardware/display.

For full validation, manual testing is required as described above.
    """
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
