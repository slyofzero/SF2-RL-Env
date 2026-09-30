# ==============================================================================
# Makefile — Shadow Fight 2 (Cat Blasters 9k) Automation Harness
# ==============================================================================
# Usage:
#   make install    - Checks for installation; installs APK if missing
#   make boot       - Checks for installation; boots the game if available
#   make reinstall  - Force re-installs the APK even if already present
#   make restart    - Force stops and reboots the game
#   make screenshot - Captures an instant sub-second BlueStacks screenshot
#   make all        - Runs install, then boots the game
# ==============================================================================

# Select virtualenv python if available, otherwise system python
PYTHON := .venv/Scripts/python.exe
ifeq ($(wildcard $(PYTHON)),)
    PYTHON := python
endif

.PHONY: all install boot reinstall restart screenshot status help

# Default target: check/install and boot
all: install boot

## install: Check if package is installed; install APK if not found
install:
	@$(PYTHON) scripts/install.py

## boot: Check if package is installed; boot the app if available
boot:
	@$(PYTHON) scripts/boot.py

## reinstall: Force reinstallation of the APK
reinstall:
	@$(PYTHON) scripts/install.py --force

## restart: Force-stop and reboot the app
restart:
	@$(PYTHON) scripts/boot.py --restart

## screenshot: Capture instant ADB screenshot to artifact directory
screenshot:
	@$(PYTHON) .agents/skills/bluestacks-instant-screenshot/scripts/screenshot.py --artifact current_screen

## status: Check device connection, installation state, and running process
status:
	@$(PYTHON) -c "from scripts.common import is_installed, is_running, find_adb, get_connected_device; adb = find_adb(); dev = get_connected_device(adb); print(f'ADB Device : {dev}'); print(f'Installed  : {is_installed()}'); print(f'Running    : {is_running()}')"

## help: Display this help message
help:
	@echo "Shadow Fight 2 Automation Makefile"
	@echo "=================================="
	@echo "Targets:"
	@echo "  make install    - Check installation; install SF2_Modded_v3.apk if missing"
	@echo "  make boot       - Check installation; boot the game on BlueStacks"
	@echo "  make all        - Run install check, then boot (default)"
	@echo "  make reinstall  - Force reinstall the APK"
	@echo "  make restart    - Force stop and reboot the game"
	@echo "  make screenshot - Instant sub-second screen capture to artifacts"
	@echo "  make status     - Check device, installation, and running status"
