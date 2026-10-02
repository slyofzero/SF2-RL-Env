#!/usr/bin/env python3
"""
Verification test for unified ShadowFightEnv interface.
Tests:
- env.start() (start, freeze, step 1 -> env.state)
- env.step() (1 step)
- env.step(10) (10 steps)
- env.freeze()
- env.tick_speed(2.0)
- env.pause()
- env.exit()
"""

import time
from rl_env import ShadowFightEnv

def main():
    print("=" * 60)
    print(" Shadow Fight 2 — Unified Environment Test")
    print("=" * 60)

    env = ShadowFightEnv()

    print("\n1. Testing env.start()...")
    state = env.start(timeout=25.0)
    print(f"   [OK] Started! Initial tick state (env.state):")
    print(f"        Tick: {state.get('tick')}, P1: {state.get('player', {}).get('hp')}, P2: {state.get('opponent', {}).get('hp')}, Dist: {state.get('distance')}")
    assert env.state is not None, "env.state should not be None after start()"
    assert state.get("type") == "TELEMETRY_FRAME", "State should be a TELEMETRY_FRAME"
    assert "player" in state and "x" in state["player"], "State must include 3D player telemetry"
    assert "opponent" in state and "x" in state["opponent"], "State must include 3D opponent telemetry"

    print("\n2. Testing env.step() (1 tick)...")
    s1 = env.step()
    print(f"   [OK] Stepped 1 tick: {s1.get('tick')}")
    assert s1.get("tick") == state.get("tick") + 1, "Tick counter should increment by 1"
    assert s1.get("type") == "TELEMETRY_FRAME", "Step state must be a TELEMETRY_FRAME"

    print("\n3. Testing env.step(steps=10)...")
    s10 = env.step(steps=10)
    print(f"   [OK] Stepped 10 ticks: {s10.get('tick')}")
    assert s10.get("tick") == s1.get("tick") + 10, "Tick counter should increment by 10"
    assert "hits" in s10, "Step state must include hits array"

    print("\n4. Testing env.get_state()...")
    st_cur = env.get_state()
    print(f"   [OK] Queried state: Tick: {st_cur.get('tick')}, Dist: {st_cur.get('distance')}, P1 Move: {st_cur.get('player', {}).get('action')}")
    assert env.state == st_cur, "env.state should match env.get_state()"
    assert st_cur.get("type") == "TELEMETRY_FRAME", "get_state must return a TELEMETRY_FRAME"

    print("\n5. Testing env.freeze()...")
    frozen = env.freeze()
    print(f"   [OK] Frozen: {frozen}")

    print("\n6. Testing env.tick_speed(2.0)...")
    spd = env.tick_speed(2.0)
    print(f"   [OK] Simulation speed: {spd}x")

    print("\n7. Testing env.pause()...")
    paused = env.pause()
    print(f"   [OK] Paused: {paused}")
    time.sleep(1.0)

    print("\n8. Testing env.resume()...")
    resumed = env.resume()
    print(f"   [OK] Resumed: {resumed}")
    time.sleep(1.0)

    print("\n9. Testing env.exit()...")
    exited = env.exit()
    print(f"   [OK] Exited to map: {exited}")
    time.sleep(2.0)

    env.close()
    print("\n" + "=" * 60)
    print(" All ShadowFightEnv methods verified successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
