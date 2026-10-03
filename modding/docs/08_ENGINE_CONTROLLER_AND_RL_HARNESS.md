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

### 2.4 Modular File Structure
The Frida JavaScript hooks are maintained in dedicated standalone `.js` files rather than embedded multiline strings:
- `scripts/frida/engine_harness.js` — Action controller, timing state machines, and `FixedUpdate` physics hook.
- `scripts/frida/telemetry_streamer.js` — 3D Vector3 coordinates, HP decryption, and `ScreenModel` hit badges.

Python wrappers (`scripts/engine_controller.py`, `scripts/stream_telemetry.py`) load these `.js` files dynamically on connection, enabling full JavaScript syntax highlighting, IDE linting, and modular testing.

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
| `+ 0xB8` | `pointer` | **Player 2** (`opponentPtr`) / opponent |
| `+ 0x10` | `pointer` | Player 1 parameter object (`PJKHAJKEHEL`) — also at `playerPtr + 0x148` |
| `+ 0x18` | `pointer` | Player 2 parameter object (`PJKHAJKEHEL`) — also at `opponentPtr + 0x148` |
| `+ 0x38` | `pointer` | Fighter list container |

### 3.4 playerPtr Memory Layout

| Offset | Type | Content |
|:---|:---|:---|
| `+ 0x148` | `pointer` | Fighter parameter object (`PJKHAJKEHEL`) containing health and stats |
| `+ 0x220` | `int32` | **Current joystick quadrant** slot. Write the active quadrant here every tick to hold direction. Write `-1` to release. |
| `+ 0x250` | `pointer` | 3D Position component (call `0x342F0CC` to get native `Vector3` struct) |
| `+ 0x258` | `pointer` | Action queue pointer (passed to `clearQueueFunc`) |

### 3.5 Health Resolution & Decryption (CodeStage ObscuredFloat)

The engine stores fighter health encrypted with CodeStage Anti-Cheat (`ObscuredFloat`) inside `PJKHAJKEHEL`:
* **Max Health**: `ObscuredFloat` at offset `+ 0xF4` (`MGLLAKLAAOO`)
* **Current Health**: `ObscuredFloat` at offset `+ 0x208` (`JNFNFEJAGGN`)
*(Note: Offset `+ 0x15c` was previously inspected during early reversing, but is `MAAJLADCKDG`, a static character gear scaling constant—which is why it read a constant `0.5176` / `1.0`).*

CodeStage anti-cheat scrambles bytes (swapping bytes 1 and 2 in `ACTkByte4`) and XORs them with a 4-byte key. The engine provides a dedicated native decryption function at RVA `0x1BC1F2C` (`ALBJPLAPOBO`):

```javascript
// Native ObscuredFloat decrypt (ALBJPLAPOBO - RVA 0x1BC1F2C)
var decryptNative = new NativeFunction(il2cppBase.add(0x1BC1F2C), 'float', ['pointer']);

var curHealth = decryptNative(pParam.add(0x208));
var maxHealth = decryptNative(pParam.add(0xF4));
var hpPercent = (maxHealth > 0) ? Math.min(1.0, Math.max(0.0, curHealth / maxHealth)) : 1.0;
```

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
ctrl.connect()  # Attaches to Gadget on port 27042

# Movements
ctrl.step(quad, ticks)  # Single timed step. quad = absolute or relative code
ctrl.hold(quad)  # Continuous walk until stop()
ctrl.dash(is_fwd=True)  # Double-tap dash forward or back
ctrl.stop()  # Halt all movement immediately

# Attacks
ctrl.attack(act_id, quad=0, hits=1)
# act_id: 9=punch, 10=kick
# quad: 0=neutral, or absolute/relative quadrant
# hits: 1=single, 2=double combo

# Speed
ctrl.set_speed(1.0)  # 1.0 = normal, 10.0 = 10× faster

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

## 9. Live JSON Telemetry Streamer (`stream_telemetry.py`)

`scripts/stream_telemetry.py` connects to Frida Gadget, dynamically loads `scripts/frida/telemetry_streamer.js`, and streams real-time fight telemetry:
* Decrypted HP for both fighters (from `0x208` / `0xF4`)
* Exact 3D Vector3 ground coordinates (`x`, `y`, `z`), facing, and distance
* Live animation states for Player and Opponent (`action`)
* Detailed hit events: `head_hit`, `critical_hit`, `shock`, `blocked_hit`, `hit` (clean damage)
* Round lifecycle events: `round_start` and `round_end` (with round number, winner, reason) — always recorded regardless of `--hits-only` filtering

```powershell
# 1. Human-readable stream (defaults to calm 1 update per second)
python ./scripts/stream_telemetry.py --pretty

# 2. Save live logs into game-logs/ in JSON Lines format (.jsonl)
python ./scripts/stream_telemetry.py --pretty --log

# 3. Custom log filename
python ./scripts/stream_telemetry.py --log fight_run1.jsonl

# 4. Custom update intervals or unthrottled live
python ./scripts/stream_telemetry.py --interval 0.5   # every 0.5s
python ./scripts/stream_telemetry.py --rate 5         # 5 updates/sec
python ./scripts/stream_telemetry.py --live           # unthrottled ~20Hz real-time
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

---

## 13. Engine Action State Machine & Master Action Catalog

### 13.1 Input Intents vs. Engine Actions
In Shadow Fight 2, there is an important distinction between **Input Intents** and **Engine Actions**:

1. **Input Intents (`engine_controller.py`)**:
   - The virtual joystick directions (`UP`, `FORWARD`, `BACK`, `DOWN`, diagonals) and action buttons (`PUNCH`, `KICK`).
   - Dispatched into `actDown` / `actUp` to simulate physical or virtual controller events.

2. **Engine Actions (`telemetry_streamer.js` / `PlayMove` RVA `0x34EC600`)**:
   - The actual animation and physical state machine clips executed by the engine.
   - Handled via `OLKKAIFGGAK.OJHIDJPICJN` (Character Action Dispatcher), which routes triggers across 16 internal event categories:
     - `EVENT_KEY_PRESSED` (Input attacks, acrobatics, and locomotion)
     - `EVENT_ANIM_START` (Automatic guard and blocking animations)
     - `EVENT_HIT` (Damage taken animations, staggers, and flinches)
     - `EVENT_ANIM_INTERRUPTED` (Knockdowns, wall hits, ground hits, and recoveries)
     - `EVENT_ROUND_STAGE` (Starting stances, victory poses, and timeout falls)

### 13.2 Master Catalog of 147 Engine Actions

#### 1. Input Strikes & Combat Attacks (`EVENT_KEY_PRESSED`)
These actions are initiated by either the player or opponent choosing an attack intent:
- **Barehanded / Fist Attacks**: `HighPunch`, `DoublePunch`, `HeavyPunch`, `LowPunch`, `SpinningPunch`, `UpperCut`, `ElbowStrike`, `ShortUpwardElbowStrike`.
- **Kicks**: `FrontKick`, `LowKick`, `BackKick`, `HighKick`, `AxeKick`, `Sweep`, `DoubleSweep`, `FrontJumpKick`, `ShortJumpKick`, `TwoFootJumpKick`, `ReverseJumpKick`, `DoubleJumpKick`, `BackFlipKick`, `DodgeKick`, `DodgeReverseKick`, `HighKneeUp`, `SuckerKick`.
- **Weapon Attacks (Equipped: Knives)**: `KnivesSlash`, `KnivesDoubleSlash`, `KnivesSuperSlash`, `KnivesHeavySlash`, `KnivesUpperSlash`, `KnivesLowSlash`, `KnivesSpinningSlash`.
- **Close-Range Throws**: `ThrowForward`, `ThrowThroughTheBack`, `ThrowSuplexVProfile`.

#### 2. Locomotion & Acrobatics (`EVENT_KEY_PRESSED` / `EVENT_WALL_HIT`)
- **Movement**: `StepForward`, `StepBack`, `DoubleStepForward`, `Duck`.
- **Rolls & Flips**: `ForwardRoll`, `BackRoll`, `FrontFlip`, `BackFlip`, `BackHandflip`.
- **Wall Bounces & Aerials**: `JumpUp`, `WallJump_50`, `WallJump_100`, `WallJump_200`, `WallJump_250`, `WallJump_50_PVP`, `WallJump_100_PVP`, `WallJump_200_PVP`, `WallJump_250_PVP`.

#### 3. Defensive Blocks & Guards (`EVENT_ANIM_START`)
Triggered automatically when a fighter is neutral or moving away while an opponent's attack enters active collision frames:
- **Standing & Mid Guards**: `HighBlock`, `HighBlockPlus`, `HighBlockHeavy`, `MiddleBlock`, `MiddleBlockPlus`, `MiddleBlockHeavy`.
- **Low & Overhead Guards**: `SweepBlock`, `SweepBlockHeavy`, `OverheadBlock`, `OverheadBlockHeavy`, `TitanBlock`.

#### 4. Hit Reactions & Stagger States (`EVENT_HIT` / `EVENT_ANIM_START`)
Triggered when an incoming attack connects unblocked:
- **Head & High Hits**: `HighHit`, `HighHitShort`, `HighHitShortPlus`, `HighHitLong`, `HighHitHeavy`, `HighHitPlus`, `HighHitFall`.
- **Body & Mid Hits**: `MiddleHit`, `MiddleHitShort`, `MiddleHitShortPlus`, `MiddleHitHeavy`, `MiddleHitPlus`, `MiddleHitFall`, `SpinningHit`, `SpinningHitHeavy`, `SpinningHitFall`.
- **Low & Sweep Hits**: `LowHit`, `LowHitHeavy`, `LowPullHitHeavy`, `SweepHit`, `SweepHitHeavy`, `SweepHitFall`.
- **Stun & Special Statuses**: `Stun`, `StunTransitionFromIdle`, `MindThrowHit`, `TitansHarpoonHit`, `TitansHarpoonStrikeFall`, `TitansHarpoonHitGrab`.

#### 5. Knockdowns, Ground States & Recoveries (`EVENT_ANIM_INTERRUPTED`)
Triggered when a hit carries knockdown momentum or sends the fighter against arena boundaries:
- **Falls & Ground Impact**: `PhysicalFall`, `PhysicalFallSuperHit`, `PhysicalGroundHit`, `PhysicalLying`.
- **Wall Collisions**: `WallHit`, `WallHitFall`.
- **Standup Recoveries**: `Standup`, `StandupBack`, `StandupAfterThrowFall`.
- **Special Boss / Item Hits**: `DirectorIcePinsPlayerHit`, `IcePinsPlayerHit`, `InvisibilityCloakPlayerHit`.

#### 6. Stances, Intros & Match Outcomes (`EVENT_ROUND_STAGE` / `NONE`)
- **Neutral & Stance Clips**: `StanceIdle`, `SetDirectionStanceIdle`, `FistsStartStanceIdle-Left`, `FistsStartStanceIdle-Right`, `KnivesStartStanceIdle`.
- **Round Intros**: `FistsStartStance-Left`, `FistsStartStance-Right`, `KnivesStartStance-Left`, `KnivesStartStance-Right`.
- **Match Endings**: `Win_Knives`, `Win_Fists`, `Loss_1`, `Loss_2`, `Loss_fall`, `TimeoutLoss`, `LossThrowForward`, `LossThrowBack`.

### 13.3 Weapon Scoping & Live Equipment Resolution
While kicks, acrobatics, blocks, throws, and hit reactions are universal across all characters, **punch and slash actions are strictly scoped by the equipped weapon**:

1. **Weapon Scoping Mechanics**:
   - A barehanded fighter (e.g. `Monkey` with `Fists`, or Shadow after a `Shock` disarm) only has fist strikes active (`HighPunch`, `DoublePunch`, `HeavyPunch`, `LowPunch`, `SpinningPunch`, `UpperCut`, `ElbowStrike`).
   - A fighter with Knives (`WEAPON_KNIVES`) replaces barehanded punch combos with dedicated knife slashes (`KnivesSlash`, `KnivesDoubleSlash`, `KnivesSuperSlash`, `KnivesHeavySlash`, `KnivesUpperSlash`, `KnivesLowSlash`, `KnivesSpinningSlash`).
   - Equipping Swords or Staff activates their respective weapon action trees (`swords_super_slash`, `staff_heavy_slash`).

2. **Native Memory Resolution**:
   - Fighter Param block: `fighter + 0x148` (`PJKHAJKEHEL`).
   - Equipped Items:
     - `+0xB8`: Skeleton (`Skeleton`)
     - `+0xC0`: Weapon (`HOOAAGABMBL`, string at `+0x18`) -> e.g. `"WEAPON_KNIVES"`, `"Fists"`
     - `+0xC8`: Armor / Body (`HOOAAGABMBL`) -> e.g. `"Body"`, `"BODY_MONKEY"`
     - `+0xD0`: Helm / Head (`HOOAAGABMBL`) -> e.g. `"Head"`, `"HEAD_MONKEY"`
     - `+0xD8`: Ranged Weapon (`HOOAAGABMBL`) -> e.g. `"NoRanged"`
     - `+0xE0`: Magic (`HOOAAGABMBL`) -> e.g. `"NoMagic"`
     - `+0x188`: Fighter Name (`string`) -> e.g. `"NAME_SHADOW"`, `"NAME_MONKEY"`
   - A singular `EQUIPMENT_INFO` event is dispatched once at the start of combat containing both fighters' complete gear profile (weapon, armor, helm, ranged, magic, and name).
   - Subsequent `ROUND_START` and periodic `TELEMETRY_FRAME` packets are kept completely clean of equipment clutter, focusing solely on kinematics, actions, health, and hit events.

### 13.4 Real-Time Round Countdown Clock (`time_left`)
The 99-second match countdown timer rendered at the top-center HUD is managed by `ViewerFight` (referenced at `battleCtrl + 0x198` (`PreFight`) $\rightarrow$ `+ 0x80` (`ViewerFight`)):
- `viewerFight + 0x90`: `ObscuredInt GJOBKIBMLHC` — **Total remaining frames** (starts at $99 \times 60 = 5940$, decrements by 1 on every single physics tick).
- `viewerFight + 0xA0`: `ObscuredInt MOBINBAJICJ` — **Total remaining seconds** (starts at 99, decrements every 60 ticks).
- `viewerFight + 0xB0`: `int KBFHMLONBPA` — Raw integer seconds rendered to `roundTimer` HUD (`LabelAlias` at `+ 0x38`).

By decrypting `viewerFight + 0x90` on every physics tick, `telemetry_streamer.js` provides high-precision sub-second time remaining (`time_left = framesLeft / 60.0`), allowing RL agents and observers to track the clock smoothly ticking away from `99.00` down to `0.00`.


---

## 14. Simulation Speed Multipliers (`timeScale`) & Pre-Round Timing Characteristics

### 14.1 How `Time.timeScale` Operates
Through Frida RPC, [`scripts/engine_controller.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/scripts/engine_controller.py) invokes `UnityEngine.Time.set_timeScale` (`0x3BFB9C0`) to accelerate simulation. In Unity, `timeScale` controls how many physics ticks (`FixedUpdate`) execute per real-world second:
$$\text{Ticks To Run Per Real Second} = \frac{\Delta t_{\text{real}} \times \text{timeScale}}{\text{fixedDeltaTime (0.01667s)}}$$

- **1x**: ~60 physics ticks per real-world second.
- **10x**: ~600 physics ticks per real-world second.
- **100x**: ~6,000 physics ticks per real-world second (CPU bound).

### 14.2 Pre-Round Intro Tick Discrepancy (444 vs 550 vs 4001 Ticks)
When inspecting the telemetry logs across different speeds, the first round's `round_start` event fires at noticeably different tick indices:
- **1x speed**: `round_start` occurs at $\approx$ **tick 444**
- **10x speed**: `round_start` occurs at $\approx$ **tick 550**
- **100x speed**: `round_start` occurs at $\approx$ **tick 4001**

#### Root Cause: Decoupling of Scaled Physics and Unscaled Wall-Clock Operations
Before `ViewerFight.Play` (`0x35BE050`) dispatches the `round_start` event, the game runs a sequence with components that **do not scale with `timeScale`**:
1. **Asynchronous Resource Deserialization**: Loading 3D meshes, skins, weapons, and particle effects from memory/storage. These background disk and memory I/O operations execute at physical hardware speed.
2. **Audio Track Synchronization**: The announcer voiceover (*"ROUND 1... FIGHT!"*) streams through Android's hardware audio buffer (OpenSL/AudioTrack). The audio track plays at normal 1.0x pitch and duration (~1.5–2.0 real seconds).
3. **Unscaled UI Transitions**: Camera pans and UI banner animations utilize `Time.unscaledDeltaTime` so visual transitions do not break when `timeScale` is adjusted.

#### Mathematical Explanation
While the engine waits for that real-world wall-clock delay ($\approx 0.8 - 2.0\text{ seconds}$), `FixedUpdate` is **already running and incrementing `tickIndex`**:

| Speed | Real-World Intro Delay | Physics Ticks Churned During Delay | Total Ticks at `round_start` |
|:---|:---|:---|:---|
| **1x** | $\approx 2.0\text{ real seconds}$ | $\approx 2.0 \times 60 = \mathbf{120\text{ ticks}}$ (+ stance anims) | **$\approx 444\text{ ticks}$** |
| **10x** | $\approx 1.5\text{ real seconds}$ (some UI skips) | $\approx 1.5 \times 350 = \mathbf{525\text{ ticks}}$ | **$\approx 550\text{ ticks}$** |
| **100x** | $\approx 0.8\text{ real seconds}$ (CPU saturated) | $\approx 0.8 \times 4,500 = \mathbf{3,600+\text{ ticks}}$ | **$\approx 4,001\text{ ticks}$** |

### 14.3 Implications for RL Harness Design
- **Never hardcode tick thresholds for match onset**: Do not assume combat begins at `tick == 444`. Always gate the RL episode step loop on the discrete `round_start` event.
- **Strict Invariance During Active Combat**: Once `round_start` has fired, all combat physics, fighter velocities, collision boxes, and damage calculations are **100% deterministic per physics tick**, irrespective of whether the game runs at 1x, 5x, or 10x simulation speed.

---

## 15. Native Game Actions API (`pause`, `resume`, `exit_fight`)

To enable a completely headless RL environment without relying on OS/emulator touch coordinates (`adb shell input tap`), game flow controls are implemented natively through IL2CPP method calls.

### 15.1 Reverse Engineered Method Targets
1. **Pause & Resume Button Handler**:
   - Class: `FCJBEKHDLAF` (`battleCtrl`)
   - Method: `OANGGKCBAOJ(battleCtrl, actionId)` (RVA `0x33F3AD8`)
   - Enum `ViewerFight.GHOHIFCGFBO`:
     - `ButtonPause = 0`: Pauses the fight and instantiates the `PauseScreen` UI.
     - `ButtonPauseSurrender = 1`: Triggers pause-menu surrender.
     - `ButtonPausePlay = 2`: Closes `PauseScreen` and resumes the fight.
2. **Immediate Match Exit / Surrender**:
   - Class: `FCJBEKHDLAF` (`battleCtrl`)
   - Method: `LPIEJMLPFBF(battleCtrl, gameOverType)` (RVA `0x33EE838`)
   - Enum `JPGAILBOMOF`:
     - `GAME_OVER_SURRENDER = -1`: Immediately terminates combat as a surrender and transitions the game scene back to `MapScene`.
3. **Pause State & Modal Tracking**:
   - Class: `PreFight` (located at `FightScene + 0x98`)
   - Field `+0x90`: `PauseScreen IHNMJKLMFMA`. When non-null, the pause modal is active; when null, the modal is closed and combat is unpaused.

### 15.2 Thread-Safe Execution via `Scene<object>.Update`
In Unity IL2CPP, invoking UI methods directly from asynchronous Frida RPC worker threads causes access violations. Furthermore, `FixedUpdate` stops ticking while paused.

To resolve this, [`scripts/frida/game_actions.js`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/scripts/frida/game_actions.js) hooks `Scene<object>.Update` (RVA `0x296FD44`), which runs continuously at 60 Hz across all game scenes on Unity's main UI thread:
```javascript
// Scheduled execution inside main-thread Update()
if (pendingAction !== null) {
    if (pendingAction === 'pause') {
        onButtonAction(battleCtrl, 0); // ButtonPause
    } else if (pendingAction === 'resume') {
        onButtonAction(battleCtrl, 2); // ButtonPausePlay
    } else if (pendingAction === 'exit') {
        surrenderAction(battleCtrl, -1); // GAME_OVER_SURRENDER
    }
    pendingAction = null;
}
```

### 15.3 CLI & Python RL Harness Usage
Both standalone CLI execution and importable Python bindings are provided in [`scripts/game_actions.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/scripts/game_actions.py):

```bash
# Query active scene and pause status
python scripts/game_actions.py status

# Native unpause / resume
python scripts/game_actions.py resume

# Native pause
python scripts/game_actions.py pause

# Native immediate match exit / surrender
python scripts/game_actions.py exit
```

In Python RL code:
```python
from scripts.game_actions import SF2GameActions

actions = SF2GameActions()
actions.connect()

# Query status: returns {'scene': 'FightScene', 'in_fight': True, 'is_paused': False, 'ticks': 120}
status = actions.get_status()

# Control combat flow with zero screen taps
actions.pause()
actions.resume()
actions.exit_fight()

actions.disconnect()
```



---

## 16. Unified RL Environment (`ShadowFightEnv`)

The class in [`rl_env/shadow_fight_env.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/rl_env/shadow_fight_env.py) is the single high-level entry point for RL training loops.

### 16.1 Architecture

`ShadowFightEnv` is a thin orchestration layer that wraps two lower-level Frida connections:

| Component | JS Hook | Responsibility |
|---|---|---|
| `SF2GameActions` | `game_actions.js` | Fight lifecycle: start, pause, resume, exit, set_rounds |
| `SF2TickController` | `tick_controller.js` | Deterministic physics: freeze/unfreeze, step, speed, state |

Both connect **independently** to the same Frida Gadget on port `27042`, each loading its respective JS hook script. This separation keeps the real-time physics control path isolated from the game-state management path, preventing message queue contention.

```
ShadowFightEnv
├── SF2GameActions  ──►  game_actions.js  ──►  Unity main thread queue
└── SF2TickController ──►  tick_controller.js  ──►  FightScene.FixedUpdate hook
```

### 16.2 Complete Method Reference

| Method | Signature | Description | Returns |
|---|---|---|---|
| `connect` | `connect()` | Explicit connect to both subsystems. Auto-called by all methods if not already connected. | `None` |
| `start` | `start(timeout=20.0)` | Arms auto-freeze, calls `start_fight()`, waits for round-start freeze event, disarms auto-freeze, steps 1 tick to produce first observation. | `TELEMETRY_FRAME dict` |
| `step` | `step(steps=None, action=None)` | Advance N physics ticks with an optional combat action dispatched on tick 0. | `TELEMETRY_FRAME dict` |
| `freeze` | `freeze()` | Halt physics tick immediately. | `bool` |
| `unfreeze` | `unfreeze()` | Resume continuous physics tick. | `bool` |
| `tick_speed` | `tick_speed(speed=None)` | Set (or get if `speed=None`) the simulation speed multiplier. `1.0` = realtime, `10.0` = 10× faster. | `float` |
| `pause` | `pause()` | Invoke native in-engine pause modal (queued to Unity main thread). | `None` |
| `resume` | `resume()` | Dismiss native pause modal (queued to Unity main thread). | `None` |
| `exit` | `exit()` | Native surrender + `MapScene` transition. Unfreezes physics first so the defeat animation plays through correctly. | `None` |
| `set_rounds` | `set_rounds(n)` | Runtime memory patch for rounds-to-win (valid range: 1–99). No APK rebuild required. | `None` |
| `get_rounds` | `get_rounds()` | Query the current patched rounds-to-win value for this session. | `int` |
| `get_state` | `get_state()` | Query the latest telemetry state without advancing the physics tick. | `TELEMETRY_FRAME dict` |
| `close` | `close()` | Detach both subsystems, restore simulation speed to `1.0×`. | `None` |

### 16.3 Telemetry State Dict

Every `step()`, `get_state()`, and `start()` call returns a `TELEMETRY_FRAME` dict with the following fields:

```json
{
  "type": "TELEMETRY_FRAME",
  "tick": 1042,
  "time_left": 87.3,
  "frozen": true,
  "speed": 1.0,
  "in_fight": true,
  "player": {
    "hp": 0.84,
    "x": -1.23,
    "y": 0.0,
    "z": 0.0,
    "facing_left": false,
    "action": "KnivesStartStanceIdle"
  },
  "opponent": {
    "hp": 1.0,
    "x": 1.45,
    "y": 0.0,
    "z": 0.0,
    "facing_left": true,
    "action": "ForwardRoll"
  },
  "distance": 268.5,
  "hits": {
    "head_hit": false,
    "critical_hit": false,
    "shock": false,
    "blocked_hit": false
  },
  "damage_delta": {
    "player": 0.0,
    "opponent": 0.0
  }
}
```

| Field | Type | Description |
|---|---|---|
| `tick` | `int` | Cumulative physics tick counter since fight start |
| `time_left` | `float` | Seconds remaining on the round timer |
| `frozen` | `bool` | Whether physics is currently halted |
| `speed` | `float` | Current simulation speed multiplier |
| `in_fight` | `bool` | `false` when a round/match has ended |
| `player.hp` / `opponent.hp` | `float` | Normalized HP in `[0.0, 1.0]` |
| `player.x/y/z` / `opponent.x/y/z` | `float` | World-space 3D position (Unity units) |
| `player.facing_left` / `opponent.facing_left` | `bool` | Character facing direction |
| `player.action` / `opponent.action` | `string` | Current animation state name |
| `distance` | `float` | Pixel-space horizontal distance between characters |
| `hits.*` | `bool` | Hit event flags latched since last tick |
| `damage_delta.player` / `damage_delta.opponent` | `float` | HP lost by each combatant since the previous tick |

### 16.4 Auto-Freeze Design (Critical)

The `start()` method uses a two-step arm/disarm protocol to guarantee the engine freezes at **exactly tick 0** of round 1, without interfering with subsequent rounds:

1. **Arm** — `enable_auto_freeze(True)` is called *before* `start_fight()`. This activates a `Interceptor.attach` hook on `ViewerFight.Play` (RVA `0x35BE050`) in the JS side.
2. **Round 1 begins** — The engine calls `ViewerFight.Play` once at the start of round 1. The hook fires, sets `isFrozen = true`, and sends an `auto_frozen_on_round_start` message to Python.
3. **Python unblocks** — `wait_for_auto_freeze()` resolves, and `enable_auto_freeze(False)` is called **immediately**.
4. **Step 1 tick** — `step(1)` is called to produce the first observation frame.

> [!CAUTION]
> The disarm (`enable_auto_freeze(False)`) in step 3 is **critical**. If it is omitted, the `ViewerFight.Play` hook remains armed and will fire again at the start of every subsequent round, freezing the engine mid-match and stalling the episode permanently.

### 16.5 Interactive REPL

`run_interactive()` launches a command-line REPL for manual testing and debugging without writing any RL loop code. Start it via:

```bash
python -m rl_env
# or
python -m rl_env --repl
```

**Full REPL command reference:**

| Command | Maps to | Description |
|---|---|---|
| `start` | `env.start()` | Start fight and freeze at tick 0+1 |
| `step <N>` | `env.step(N)` | Advance N ticks |
| `step <N> <action>` | `env.step(N, action)` | Advance N ticks with action |
| `<N>` | `env.step(N)` | Shorthand for `step <N>` |
| `f` / `freeze` | `env.freeze()` | Freeze physics |
| `u` / `unfreeze` | `env.unfreeze()` | Resume continuous physics |
| `speed <N>` | `env.tick_speed(N)` | Set simulation speed multiplier |
| `pause` | `env.pause()` | Native in-engine pause modal |
| `resume` | `env.resume()` | Dismiss native pause modal |
| `exit` | `env.exit()` | Surrender and return to map |
| `rounds <N>` | `env.set_rounds(N)` | Patch rounds-to-win at runtime |
| `rounds` | `env.get_rounds()` | Show current patched round count |
| `state` / `status` | `env.get_state()` | Print full telemetry JSON |
| `p`, `k`, `wp`, `dpp`, … | `env.step(6, action)` | Combat move shorthand (6 ticks) |
| `q` / `quit` | exit | Exit REPL and close env |

### 16.6 Example RL Step Loop

```python
from rl_env import ShadowFightEnv

env = ShadowFightEnv()
env.set_rounds(1)  # First-to-1 for fast episodes
env.tick_speed(5.0)  # 5× faster training

state = env.start()  # Arm auto-freeze, start fight, freeze at tick 0
prev_p2_hp = state["opponent"]["hp"]

done = False
while not done:
    action = policy(state)  # your RL policy
    state = env.step(steps=6, action=action)  # 6 ticks per step ≈ 1 action frame

    p1_hp = state["player"]["hp"]
    p2_hp = state["opponent"]["hp"]
    reward = (prev_p2_hp - p2_hp) - (state.get("damage_delta", {}).get("player", 0.0))
    done = not state.get("in_fight", True)
    prev_p2_hp = p2_hp

env.exit()
env.close()
```

---

## 17. Dynamic Round Count Patching (`set_rounds`)

### 17.1 Overview

`SF2GameActions.set_rounds(n)` patches **3 IL2CPP instructions** in the running game process at runtime via Frida's `Memory.patchCode()`. No APK rebuild or relaunch is required — the patch takes effect from the next fight start.

This is the cleanest way to control episode length during RL training:
- `set_rounds(1)` → first-to-1, fastest possible episode resets
- `set_rounds(3)` → standard SF2 match (default)
- `set_rounds(99)` → effectively infinite (useful for extended rollouts)

### 17.2 ELF Load Bias Discovery

The original APK build script ([`build_cat_blasters.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/pipeline/build_cat_blasters.py)) uses raw ELF file offsets. However, Android loads the executable segment with an alignment delta derived from the ELF program header:

```
p_vaddr  = 0x18B699C
p_offset = 0x18B299C
bias     = p_vaddr - p_offset = 0x4000
```

Therefore:

$$\text{Virtual RVA (runtime)} = \text{File Offset} + \texttt{0x4000}$$

All addresses passed to `Memory.patchCode()` must use the **runtime virtual RVAs**, not the raw file offsets.

### 17.3 Corrected Virtual Memory Addresses

| File Offset | Virtual RVA (runtime) | Register | Instruction | Role |
|---|---|---|---|---|
| `0x33E7D80` | **`0x33EBD80`** | `w22` | `mov w22, #N` | Victory comparator in `DHKCOFBMIEL` |
| `0x33E9444` | **`0x33ED444`** | `w8` | `mov w8, #N` | Match statistics threshold in `AIFOMGABBBA` |
| `0x33EA8E4` | **`0x33EE8E4`** | `w1` | `mov w1, #N` | RoundModel initialization in `LPIEJMLPFBF` |

All three must be patched atomically to keep the game's internal round-win counters consistent.

### 17.4 ARM64 Encoding

The `arm64Movz(reg, imm)` helper in `game_actions.js` encodes a `MOVZ Wd, #imm` instruction directly:

```
Opcode = 0x52800000 | ((imm & 0xFFFF) << 5) | (reg & 0x1F)
```

**Example** — `N=2, reg=22` (w22):

```
0x52800000 | (2 << 5) | 22  =  0x52800056
Disassembly: mov w22, #2
```

The 4-byte little-endian encoding is written to each patched address.

### 17.5 Patch Safety

> [!IMPORTANT]
> Several safety guarantees are built into the patching design:

- **`Memory.patchCode()` only** — Frida's dedicated code-patching API is used (not the raw `Memory.protect + writeU32` pattern). `Memory.patchCode()` handles Android SELinux W^X page protection internally and is safe to call on executable pages.
- **Original-byte restoration on reload** — On script reload, the previously patched bytes at the old (incorrect) addresses are restored to their original values before the correct addresses are patched. This prevents memory corruption if the script is reloaded mid-session.
- **Session bookkeeping** — The `getRounds()` RPC export tracks the last patched value at the JS side, allowing Python to query the current round count without maintaining separate state.

---

## 18. SF2TickController (`tick_controller.py` / `tick_controller.js`)

### 18.1 Frida Hook Architecture

[`tick_controller.js`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/scripts/frida/tick_controller.js) hooks `FightScene.FixedUpdate` via `Interceptor.replace` (not `Interceptor.attach`) to gain full call-site control. On every physics tick, the replacement function runs the following decision tree:

```
FixedUpdate called by Unity engine
│
├─ isFrozen AND stepBudget == 0  →  skip origFixedUpdate()   [physics HALTED]
│
├─ stepBudget > 0                →  call origFixedUpdate()
│                                    decrement stepBudget
│                                    if stepBudget == 0:
│                                        send "step_done" + readState()  →  Python
│
└─ not frozen                    →  call origFixedUpdate()   [continuous play]
```

The **auto-freeze hook** is a separate `Interceptor.attach` on `ViewerFight.Play` (RVA `0x35BE050`). When armed (`autoFreezeEnabled = true`), it sets `isFrozen = true` and sends `auto_frozen_on_round_start` to Python exactly once at the start of a round.

### 18.2 Python API

[`SF2TickController`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/scripts/tick_controller.py) exposes the following methods:

| Method | Description | Returns |
|---|---|---|
| `connect()` | Attach to Frida Gadget on port 27042, load and inject `tick_controller.js`. | `None` |
| `freeze()` | Call `rpc.freeze()` — sets `isFrozen = true` in JS, halts the physics tick. | `bool` |
| `unfreeze()` | Call `rpc.unfreeze()` — clears `isFrozen`, resumes continuous physics. | `bool` |
| `step(num_ticks=1, action=None)` | Call `rpc.step(n, quad, btn)`, then block on the `step_done` message event. Returns the telemetry state attached to the `step_done` message. | `TELEMETRY_FRAME dict` |
| `set_speed(speed)` | Call `rpc.set_speed(speed)` — sets the Unity `Time.timeScale` multiplier. | `float` |
| `enable_auto_freeze(flag)` | Call `rpc.set_auto_freeze(flag)` — arm or disarm the `ViewerFight.Play` hook. | `None` |
| `wait_for_auto_freeze(timeout=30.0)` | Block on a `threading.Event` until the `auto_frozen_on_round_start` message is received from JS, or raise `TimeoutError`. | `None` |
| `get_state()` | Call `rpc.get_state()` synchronously — returns the current telemetry snapshot without advancing the tick. | `TELEMETRY_FRAME dict` |
| `disconnect()` | Unload the injected script and detach the Frida session. | `None` |

### 18.3 Action Dispatch in `step()`

Before calling `rpc.step(n, quad, btn)`, the `step()` method resolves the human-readable `action` string via the `ACTION_MAP` lookup table into a `(quad, btn)` tuple:

```python
# Example entries in ACTION_MAP
ACTION_MAP = {
    "p": (0, "punch"),
    "k": (0, "kick"),
    "wp": (0, "weapon_punch"),
    "dpp": (2, "punch"),  # down-forward + punch
    # ... full directional × button matrix
}

quad, btn = ACTION_MAP[action]
rpc.step(num_ticks, quad, btn)
```

The JS hook dispatches the action on **tick 0** of the step budget — the action fires on the very first tick advanced, and the remaining `n-1` ticks let the animation and physics consequences play out. This ensures the action input is registered at the earliest possible moment within the step window.
