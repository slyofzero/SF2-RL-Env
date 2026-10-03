# Next Milestones & Feature To-Do List

This document outlines upcoming architectural enhancements and gameplay configuration features planned for the Shadow Fight 2 Reinforcement Learning & Modding Environment.

---

## 1. High-Priority Infrastructure: Lightweight & Headless Emulator Migration

### Context & Objectives
While BlueStacks 5 served as a reliable visual testbed during reverse engineering and initial APK verification, training RL models (e.g., PPO/SAC) requires high throughput, multi-instance parallelization (vectorized environments), and minimal resource overhead.

Because `ShadowFightEnv` operates purely over TCP socket (`port 27042` via Frida Gadget) with zero coordinate touch dependencies, the codebase is already 100% emulator-agnostic.

### To-Do Items
- [ ] **Docker + ReDroid Setup (WSL2 / Linux)**:
  - Create a `docker-compose.yml` defining an isolated Android 11 container (`redroid/redroid:11.0.0-latest`).
  - Configure GPU passthrough / software rendering (`androidboot.redroid_gpu_mode=guest` or `host`).
  - Set up automatic APK provisioning and headless auto-launch of `com.nekki.catblasters`.
  - Expose ports `5555` (ADB) and `27042` (Frida Gadget).
  - Verify headless combat stepping, physics speedups (10x–50x), and telemetry capture.
- [ ] **Android Studio AVD Profile (Native Windows/Linux Alternative)**:
  - Configure a dedicated ARM64 AVD image script.
  - Implement a dual-mode launcher script supporting both:
    - **Headless mode**: `emulator -avd SF2_ARM64 -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect`
    - **GUI mode**: `emulator -avd SF2_ARM64` (for visual inspection and policy rendering).
- [ ] **Multi-Worker Vectorized Harness**:
  - Test running multiple parallel headless containers/AVD instances on distinct port mappings (`27042`, `27043`, `27044`, ...).
  - Implement a multi-instance adapter for `gymnasium.vector.AsyncVectorEnv` or `SyncVectorEnv`.

---

## 2. In-Engine Match & Sparring Parameterization

To train generalist combat policies and implement curriculum learning, the environment needs to configure matches dynamically without manual menu navigation.

### A. Opponent Selection
- [ ] **Dynamic Opponent Switching**:
  - Expose `env.set_opponent(name: str)` (e.g., `"Monkey"`, `"Shin"`, `"Ninja"`, `"Brick"`, `"Lynx"`, `"Shogun"`, or custom sparring dummy).
  - Target IL2CPP fight initializer in `FightScene` / `InfoBattle` to inject the opponent fighter ID into `PJKHAJKEHEL` before match start.
  - Neutralize enemy AI scripts for passive sparring dummy mode (freezing opponent action selection while preserving physics and damage reactions).

### B. Player & Opponent Gear Customization
- [ ] **Player Weapon & Equipment Selection**:
  - Expose `env.set_player_gear(weapon=..., armor=..., helm=..., ranged=..., magic=...)`.
  - Support weapon classes to unlock respective action sub-trees:
    - Barehanded (`"Fists"`)
    - Knives (`"WEAPON_KNIVES"`)
    - Swords (`"WEAPON_SWORDS"`)
    - Staff (`"WEAPON_STAFF"`)
    - Daggers / Claws / Nunchaku
  - Inject gear IDs directly into `playerPtr + 0x148` (`PJKHAJKEHEL`) or `users.xml` live inventory cache.
- [ ] **Opponent Gear Customization**:
  - Expose `env.set_opponent_gear(...)` to customize the sparring partner's loadout and armor tiers.
  - Enable asymmetric stat scaling (e.g., infinite health punching dummy vs. lethal boss attack power).

### C. Combat Arena & Location Selection
- [ ] **Arena / Background Selection**:
  - Expose `env.set_location(arena_id: str)` (e.g., `"dojo"`, `"rooftop"`, `"tournament_act1"`, `"gates_of_shadows"`).
  - Hook arena asset loading in `FightScene` to dynamically swap arena prefabs and boundary limits.

---

## 3. High-Level RL Interface Completion (Gymnasium Milestone)

- [ ] **Gymnasium Environment Wrapper (`gymnasium.Env`)**:
  - Build `gymnasium` compliant subclass (`SF2GymEnv`) implementing standard `reset()`, `step(action)`, `observation_space`, and `action_space`.
  - Formalize discrete action space mapping integer actions $\to$ engine actions (`ACTION_MAP`).
  - Define composite observation dictionary (numeric vector state + optional grayscale frame capture).
- [ ] **Episode Reset & Auto-Rematch**:
  - Implement fast in-memory soft reset upon match completion (rewriting HP and resetting clock without exiting to `MapScene`).
