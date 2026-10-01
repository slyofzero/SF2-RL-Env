# 08 — Native In-Engine Action Controller & RL Harness

> **Scope**: Everything needed to understand, reproduce, and extend the Frida-based native engine controller for Shadow Fight 2 (`scripts/engine_controller.py`) and the telemetry streamer (`scripts/test_engine_api.py`).

---

## 1. Overview & Architecture

The engine controller replaces **all** touch/input emulation with direct native C++ function calls inside the game process. Instead of simulating screen taps through ADB → Android input → Unity, every action is dispatched as a `NativeFunction` call embedded directly inside the game's own physics loop (`FightScene.FixedUpdate`).

```
Old (BlueStacks Touch):
  Python → ADB → Android OS input sampler (60Hz fixed) → Unity → Game logic

New (Native Engine):
  Python → Frida RPC → JS injected inside FixedUpdate tick → NativeFunction(actDown/actUp)
```

**Key consequence**: timing is expressed in **physics ticks**, not wall-clock milliseconds. At `speed 10x`, every tick is 10× faster in real time but the action state machines fire identically every tick. This makes all actions fully speed-invariant and suitable for RL training at accelerated simulation speeds.

---

## 2. Prerequisites

### 2.1 APK
Use **`SF2_Modded_v8.apk`** (or later). It has the Frida Gadget embedded unconditionally in `lib/arm64-v8a/libfrida-gadget.so` and loaded via `AssetExtractor.smali` on every boot — including warm boots.

Earlier builds (`v7`) had the Gadget but `AssetExtractor.smali` returned early on warm boots (once `.provisioned_v4` existed), skipping `System.loadLibrary("frida-gadget")`. This was fixed in v8 by replacing `return-void` with `goto :goto_0`.

### 2.2 Port Forward
The Gadget listens on Android port 27042. Forward it to localhost before connecting:

```powershell
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" forward tcp:27042 tcp:27042
```

This must be run once per BlueStacks session. It is idempotent — safe to run again if the connection drops.

### 2.3 Python Environment
```powershell
# From repo root
.venv\Scripts\python.exe -m pip install frida
```

The `.venv` is managed by `uv` (Python 3.12). `frida` version must match the Gadget version embedded in the APK (v17.19.0).

---

## 3. IL2CPP Reverse Engineering Findings

All offsets are **relative to the IL2CPP base** (not the raw SO load address). The base is calculated at runtime by enumerating executable memory ranges and subtracting the known file offset `0x18b6000`:

```javascript
var ranges = Process.enumerateRanges('r-x');
for (var i = 0; i < ranges.length; i++) {
    if (ranges[i].file && ranges[i].file.path.indexOf('libil2cpp.so') !== -1) {
        il2cppBase = ranges[i].base.sub(0x18b6000);
        break;
    }
}
```

> **Why not `Process.findModuleByName`?** BlueStacks uses arm64 translation. `findModuleByName("libil2cpp.so")` returns null. Range enumeration always works.

### 3.1 Core Action Functions

| Symbol | RVA | Signature | Description |
|:---|:---|:---|:---|
| `OLKKAIFGGAK.IKPHKLHDNMA` | `0x34E90D0` | `void(playerPtr, int actionId)` | Universal **ActionDown** — press/hold a button or direction |
| `OLKKAIFGGAK.IJDCCIGHPHJ` | `0x34F57E0` | `void(playerPtr, int actionId)` | Universal **ActionUp** — release a button or direction |
| `IPCACEBFONO.DGLJCGNHLIG` | `0x34E1B54` | `void(queuePtr)` | Clear the action queue held at `playerPtr + 0x258` |
| `Stick.get_Instance` | `0x3068B44` | `Stick*()` | Get the virtual joystick singleton |
| `Stick.ReleaseInput` | `0x306A558` | `void(stickPtr)` | Force-release the on-screen joystick |
| `UnityEngine.Time.set_timeScale` | `0x3BFB9C0` | `void(float)` | Set simulation speed multiplier |

### 3.2 Master Physics Loop

| Symbol | RVA | Description |
|:---|:---|:---|
| `FightScene.FixedUpdate` (hook target) | `0x33F2A54` | Called every physics tick (~60Hz at 1x speed). `args[0]` = `battleCtrl` pointer |

### 3.3 battleCtrl Memory Layout (from `args[0]` of hook)

| Offset | Type | Content |
|:---|:---|:---|
| `+ 0xB0` | `pointer` | **Player 1** (`playerPtr`) — Shadow |
| `+ 0xB8` | `pointer` | **Player 2** / opponent |
| `+ 0x98` | `pointer` | Player 1 parameter object (health, stats) |
| `+ 0xA0` | `pointer` | Player 2 parameter object |
| `+ 0x38` | `pointer` | Fighter list container |

### 3.4 playerPtr Memory Layout

| Offset | Type | Content |
|:---|:---|:---|
| `+ 0x220` | `int32` | **Current joystick quadrant** slot. Write the active quadrant here every tick to hold direction. Write `-1` to release. |
| `+ 0x258` | `pointer` | Action queue pointer (passed to `clearQueueFunc`) |

### 3.5 Health Decryption (CodeStage ObscuredFloat)

The game uses CodeStage Anti-Cheat `ObscuredFloat`. The encrypted value at `paramPtr + 0x15c` is decrypted as:

```javascript
function decryptObscuredFloat(ptr) {
    var k = ptr.readS32();       // crypto key
    var v = ptr.add(4).readS32(); // encrypted value
    var buf = Memory.alloc(4);
    buf.writeS32(k ^ v);          // XOR to recover raw IEEE 754 bits
    return buf.readFloat();
}
```

Player 1 HP: `decryptObscuredFloat(battleCtrl.add(0x98).readPointer().add(0x15c))`  
Player 2 HP: `decryptObscuredFloat(battleCtrl.add(0xA0).readPointer().add(0x15c))`

### 3.6 Ground Position (Spatial Facing)

Fighter world X positions are read via:

```javascript
// battleCtrl + 0x38 → list → items array
var listPtr = battleCtrl.add(0x38).readPointer();
var items   = listPtr.add(0x10).readPointer();
var f1 = items.add(0x20).readPointer(); // fighter 1 GameObject
var f2 = items.add(0x28).readPointer(); // fighter 2 GameObject

// GameObject → component at +0xE0 → position at +0x10 → X float at +0x10
var pos1 = f1.add(0xE0).readPointer().add(0x10).readPointer();
var p1_x = pos1.add(0x10).readFloat();
```

Facing direction: `isFacingLeft = (p1_x > p2_x)` — if Shadow's X is greater than the opponent's, Shadow is facing left.

### 3.7 PlayMove Hook (Animation Verification)

Used during calibration to confirm which animations trigger. Not required for production.

| Symbol | RVA | Description |
|:---|:---|:---|
| `NFJPOGJJEAK` (PlayMove) | `0x34EC600` | Called when engine commits to an animation. `args[1]` = move definition object. Move name string at `args[1] + 0x68` → pointer → UTF-16 string at `+0x14` (length at `+0x10`). |

---

## 4. The Quadrant System

SF2 uses a **8-sector joystick** mapped to integer quadrant IDs:

```
        1 (Up)
   8         2
(Up-L)     (Up-R)
7               3
(Left)       (Right)
   6         4
(Dn-L)     (Dn-R)
        5 (Down)
```

Action IDs extend this numbering for attack buttons:

| ID | Action |
|:---|:---|
| `1` | Jump / Up |
| `2` | Up-Right |
| `3` | Right (Forward when facing right) |
| `4` | Down-Right |
| `5` | Down / Duck |
| `6` | Down-Left |
| `7` | Left (Forward when facing left) |
| `8` | Up-Left |
| `9` | **Punch / Knife Slash** |
| `10` | **Kick** |
| `0` | Release / Neutral |
| `-1` | Clear quadrant slot (write to `playerPtr + 0x220`) |

### 4.1 Relative Quadrant Codes

The controller uses **relative codes** that are resolved to absolute quadrants at runtime based on the live facing direction:

| Relative Code | Facing Right → Absolute | Facing Left → Absolute | Semantic |
|:---|:---|:---|:---|
| `-2` | `3` (Right) | `7` (Left) | **Forward** |
| `-3` | `7` (Left) | `3` (Right) | **Backward** |
| `-4` | `2` (Up-Right) | `8` (Up-Left) | **Up-Forward** (`wd`) |
| `-5` | `8` (Up-Left) | `2` (Up-Right) | **Up-Backward** (`wa`) |
| `-6` | `4` (Down-Right) | `6` (Down-Left) | **Down-Forward** (`sd`) |
| `-7` | `6` (Down-Left) | `4` (Down-Right) | **Down-Backward** (`sa`) |

Resolution happens inside `resolveQuadrant(quad)` which reads `isFacingLeft` — a variable updated every tick from live coordinates.

---

## 5. State Machines Inside FixedUpdate

All three state machines run inside the `Interceptor.attach(masterTickAddr, { onEnter })` callback. They operate on shared variables and are advanced by one step per physics tick.

### 5.1 Cardinal / Compound Movement

**Variables**: `isContinuousHold`, `activeMoveQuad`, `moveTicksRemaining`, `moveJustStarted`

```
Trigger: stepMove(quad, ticks)  OR  holdMove(quad)

Each tick:
  If continuous hold:
    → Write activeMoveQuad to playerPtr+0x220 every tick (hold forever until stopMove())
    → Call actDown once on first tick (moveJustStarted flag)

  If timed step (ticks > 0):
    → Write activeMoveQuad to playerPtr+0x220
    → Call actDown once on first tick
    → Decrement moveTicksRemaining each tick
    → When 0: haltMovement() + send STEP_DONE
```

**Default tick counts** (at 1x speed ≈ 16.6ms per tick):

| Command | Ticks | ~Duration |
|:---|:---|:---|
| `w` (jump) | 14 | ~233ms |
| `s` (duck) | 16 | ~266ms |
| `a`, `d` (step) | 18 | ~300ms |
| `wa`, `wd` (jump diagonal) | 18 | ~300ms |
| `sa`, `sd` (roll) | 22 | ~366ms |

### 5.2 Fast Movement (Dash / Backflip)

**Variables**: `dashPhase` (0–3), `dashQuad`, `dashWaitTicks`

```
Trigger: triggerDash(isFwd)

Phase 1 (tap 1):
  → Write dashQuad + actDown + actUp + clear → dashWaitTicks = 4

Phase 2 (inter-tap gap, 4 ticks):
  → Count down dashWaitTicks
  → When 0: write dashQuad + actDown → dashWaitTicks = 18, phase 3

Phase 3 (hold, 18 ticks):
  → Count down dashWaitTicks
  → When 0: actUp + clear + haltMovement() → send DASH_DONE, phase 0
```

The 4-tick gap between taps (~65ms) lands within the engine's double-tap detection window. The 18-tick hold (~300ms) sustains the dash animation.

### 5.3 Attack State Machine

**Variables**: `attackPhase` (0–3), `currentAttackAct`, `currentAttackQuad`, `currentEffectiveQuad`, `comboTotalTaps`, `comboTapIndex`, `comboWaitTicks`, `holdQuadTicks`

```
Trigger: triggerAttack(actId, quad, hits)

Phase 1 (fire first strike):
  → Resolve effective quad from relative quad code
  → If directional: write quad to playerPtr+0x220 + actDown(quad)
  → actDown(attackAct) + actUp(attackAct)
  → If hits > 1: comboWaitTicks = 9, phase 3
  → If hits == 1: holdQuadTicks = 12, phase 2

Phase 2 (hold quadrant for 12 ticks / ~200ms):
  → Count down holdQuadTicks
  → When 0: actUp(quad) + clear quad + send ATTACK_EXECUTED, phase 0

Phase 3 (combo tap wait, 9 ticks / ~150ms per gap):
  → Count down comboWaitTicks
  → When 0: actDown(attackAct) + actUp(attackAct), increment comboTapIndex
  → If more taps remain: comboWaitTicks = 9
  → If all taps done: holdQuadTicks = 12, phase 2
```

> **Critical discovery**: Releasing the directional quadrant on the same frame as the attack button press (0ms hold) causes `NKOIBKNPICN.FAGKGMMBPNG` (the combo solver) to cancel the directional modifier. The quadrant **must** be held for ≥10 physics ticks after the attack fires. 12 ticks was chosen as the reliable threshold.

> **Close-range threshold**: When Shadow is within grapple range of the punching bag/opponent, punches convert to close-range elbow strikes (`ShortUpwardElbowStrike`) regardless of directional input. Step back (`a` or `sa`) before testing knife slash commands.

---

## 6. Full Action Vocabulary

### 6.1 Basic Movements

| Command | Quad | Ticks | Animation |
|:---|:---|:---|:---|
| `w` | `1` (Up) | 14 | Jump |
| `s` | `5` (Down) | 16 | Duck / Crouch |
| `a` | `-3` (Back) | 18 | Step Backward |
| `d` | `-2` (Fwd) | 18 | Step Forward |
| `hold a` | `-3` | ∞ | Continuous walk backward |
| `hold d` | `-2` | ∞ | Continuous walk forward |

### 6.2 Compound Movements

| Command | Quad | Ticks | Animation |
|:---|:---|:---|:---|
| `wa` | `-5` (Up-Back) | 18 | Jump Backward |
| `wd` | `-4` (Up-Fwd) | 18 | Jump Forward |
| `sa` | `-7` (Dn-Back) | 22 | Roll Backward |
| `sd` | `-6` (Dn-Fwd) | 22 | Roll Forward |

### 6.3 Fast Movements (Double-Tap)

| Command | Direction | Animation |
|:---|:---|:---|
| `dd` | Forward (`-2`) | Forward Dash / Hop |
| `aa` | Backward (`-3`) | Backflip / Backward Dash |

### 6.4 Basic Attacks

| Command | Act | Quad | Hits | Animation |
|:---|:---|:---|:---|:---|
| `p` | `9` | `0` | 1 | Neutral Knife Slash |
| `pp` | `9` | `0` | 2 | Double Knife Slash |
| `k` | `10` | `0` | 1 | Neutral Kick |
| `kk` | `10` | `0` | 2 | Double Kick |

### 6.5 Compound Attacks

| Command | Act | Quad | Animation |
|:---|:---|:---|:---|
| `wp` | `9` | `1` (Up) | `KnivesUpperSlash` (Upward Rising Slash) |
| `sp` | `9` | `5` (Down) | `KnivesLowSlash` (Low Knife Slash) |
| `ap` | `9` | `-3` (Back) | `KnivesSpinningSlash` (Spinning Back Slash) |
| `dp` | `9` | `-2` (Fwd) | `KnivesHeavySlash` (Forward Knife Slash) |
| `wk` | `10` | `1` (Up) | `ShortJumpKick` / Jump Kick |
| `sk` | `10` | `5` (Down) | `LowKick` / Sweep |
| `ak` | `10` | `-3` (Back) | `FrontKick` / Back Kick |
| `dk` | `10` | `-2` (Fwd) | `HighKneeUp` / Forward Step Kick |

### 6.6 Diagonal Kicks

| Command | Act | Quad | Animation |
|:---|:---|:---|:---|
| `wdk` | `10` | `-4` (Up-Fwd) | `FrontJumpKick` |
| `wak` | `10` | `-5` (Up-Back) | `HighKneeUp` |
| `sdk` | `10` | `-6` (Dn-Fwd) | `HighKneeUp` |
| `sak` | `10` | `-7` (Dn-Back) | `DodgeKick` |

### 6.7 Double Attacks (2-Hit Combos)

| Command | Act | Quad | Hits | Animation Chain |
|:---|:---|:---|:---|:---|
| `dpp` | `9` | `-2` | 2 | `KnivesHeavySlash` → `KnivesSuperSlash` (**Super Slash!**) |
| `app` | `9` | `-3` | 2 | Back Double Slash |
| `spp` | `9` | `5` | 2 | Low Double Slash |
| `wpp` | `9` | `1` | 2 | Upward Double Slash |
| `dkk` | `10` | `-2` | 2 | Forward Double Kick |
| `akk` | `10` | `-3` | 2 | Back Double Kick |
| `skk` | `10` | `5` | 2 | Low Double Sweep |
| `wkk` | `10` | `1` | 2 | Flying Double Kick |

---

## 7. Python API (`SF2EngineController`)

The `SF2EngineController` class in `scripts/engine_controller.py` wraps all Frida RPC calls.

```python
from scripts.engine_controller import SF2EngineController

ctrl = SF2EngineController()
ctrl.connect()      # Attaches to Gadget on port 27042

# Movements
ctrl.step(quad, ticks)   # Single timed step. quad = absolute or relative code
ctrl.hold(quad)           # Continuous walk until stop()
ctrl.dash(is_fwd=True)   # Double-tap dash forward or back
ctrl.stop()               # Halt all movement immediately

# Attacks
ctrl.attack(act_id, quad=0, hits=1)
# act_id: 9=punch, 10=kick
# quad: 0=neutral, or absolute/relative quadrant
# hits: 1=single, 2=double combo

# Speed
ctrl.set_speed(1.0)   # 1.0 = normal, 10.0 = 10× faster

# Telemetry
status = ctrl.get_status()
# Returns: { connected, player_hp, opponent_hp, facing_left }
```

All movement and attack methods **block** until their action completes (via threading.Event), with a generous timeout fallback. This makes them safe to call sequentially in an RL step loop.

---

## 8. Running the Interactive Controller

```powershell
# 1. Ensure Frida port is forwarded
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" forward tcp:27042 tcp:27042

# 2. Launch game (SF2_Modded_v8.apk), navigate to Dojo or any fight

# 3. Run interactive controller
.venv\Scripts\python.exe ./scripts/engine_controller.py
```

The controller prints `[SUCCESS] Attached to live game engine!` on successful connection, then shows the full help menu. Type any command and press Enter. The action executes immediately and the outcome is printed on the next line:

```
SF2-Engine > wp
 -> Compound Attack: UPWARD RISING SLASH (wp)
SF2-Engine > dpp
 -> Double Attack: FORWARD DOUBLE SLASH / SUPER SLASH (dpp)
SF2-Engine > speed 2.0
 -> Simulation Speed set to 2.0x
SF2-Engine > status
 -> Status: Engine Active | Shadow HP: 100.0% | Facing: RIGHT
```

---

## 9. Telemetry Streamer (`test_engine_api.py`)

`scripts/test_engine_api.py` runs a parallel Frida session that streams live state at ~20Hz without dispatching any actions. It decrypts HP, reads ground positions, facing direction, distance, and hooks hit badge events.

```powershell
.venv\Scripts\python.exe ./scripts/test_engine_api.py
```

Output format:
```
[TICK]  P1_HP=0.847  P2_HP=0.931  P1_x=-2.41  P2_x=1.83  dist=4.24  facing=RIGHT
[HIT]   CRITICAL HIT on Player 2
```

---

## 10. Simulation Speed

`speed <val>` calls `UnityEngine.Time.set_timeScale` at RVA `0x3BFB9C0`.

- At `speed 1.0`: 1 tick ≈ 16.6ms real time (60Hz physics)
- At `speed 10.0`: 1 tick ≈ 1.6ms real time (600Hz effective)

Because all timing is expressed in **ticks** (not milliseconds), all action state machines remain correct at any speed. A `step(quad, ticks=18)` always steps for exactly 18 physics frames regardless of wall-clock speed. This is the fundamental design property that makes the controller RL-ready.

---

## 11. Next Steps — Gymnasium Environment

With this controller in place, wrapping SF2 into a standard `gymnasium.Env` requires:

1. **Action Space** — `Discrete(N)` where each integer maps to one of the calibrated `ctrl.attack()` / `ctrl.step()` / `ctrl.dash()` calls from the vocabulary above.

2. **Observation Space** — Call `ctrl.get_status()` (HP, facing) + optional DXcam/ADB frame capture at 84×84 grayscale stacked frames.

3. **Reward** — HP delta: `reward = (last_p2_hp - current_p2_hp) - (last_p1_hp - current_p1_hp)`

4. **Reset** — When either HP reaches 0, restart the round. In the Dojo, this can be done by navigating back to the menu and re-entering, or by implementing a soft HP reset via Frida memory write.

5. **Step** — Call `env.step(action)` → dispatch action via controller → wait for `ATTACK_EXECUTED` / `STEP_DONE` event → read telemetry → return `(obs, reward, done, info)`.

---

## 12. Known Limitations & Gotchas

| Issue | Root Cause | Mitigation |
|:---|:---|:---|
| Directional attacks fire as elbow strikes | Shadow is within grapple range of bag/opponent | Step back once (`a`) before testing punch directions |
| `Process.findModuleByName("libil2cpp.so")` returns null | BlueStacks arm64 translation | Use `Process.enumerateRanges('r-x')` to find base |
| Port 27042 connection fails on warm boot | Old v7 smali returned early, skipping `loadLibrary` | Use SF2_Modded_v8.apk which unconditionally loads Gadget |
| Quadrant cleared same frame as attack → neutral move | Engine combo solver cancels directional modifier in 0ms | Hold quadrant for ≥12 ticks after attack fires (Phase 2) |
| `actUp` / `actDown` on wrong pointer → crash | playerPtr can be null during scene transitions | All calls gated by `if (!playerPtr || playerPtr.isNull()) return` |
