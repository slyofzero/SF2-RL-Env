# Troubleshooting BlueStacks Screenshots

### 1. Connection Refused on Port 5037 (`[WinError 10061]`)
- **Cause**: The ADB daemon is not running on the host machine.
- **Solution**: `screenshot.py` automatically attempts to start the daemon in the background via `HD-Adb.exe server nodaemon`. If running manually, execute:
  ```powershell
  & "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" start-server
  ```

### 2. "Device Offline" or "Device Not Found"
- **Cause**: BlueStacks has ADB disabled in its engine configuration.
- **Solution**:
  1. Open BlueStacks Settings -> **Advanced** -> Turn **Android Debug Bridge** to **ON**.
  2. Or check `C:\ProgramData\BlueStacks_nxt\bluestacks.conf`:
     ```ini
     bst.enable_adb_access="1"
     ```
  3. Verify with:
     ```powershell
     & "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" devices
     ```

### 3. Multiple Devices Error (`error: more than one device/emulator`)
- **Cause**: BlueStacks often registers both `127.0.0.1:5555` and `emulator-5554`.
- **Solution**: `screenshot.py` automatically binds directly to `emulator-5554` or queries device status. You can explicitly pass `-s emulator-5554`.

### 4. PowerShell Corrupting Screenshots
- **Cause**: Running `adb exec-out ... > output.png` in PowerShell triggers string redirection which converts raw 8-bit bytes to 16-bit UTF-16 characters (`FF FE ...`).
- **Solution**: Always use `screenshot.py` which writes in raw binary mode (`open(path, 'wb')`), or use `adb pull` as an alternative.
