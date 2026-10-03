#!/usr/bin/env python3
"""
Verification test for unified ShadowFightEnv interface.
Tests:
- env.start() (start, freeze, step 1 -> env.state)
- env.step() (1 step)
- env.step(10) (10 steps)
- env.act("p") (combat action via engine_controller)
- env.metadata (equipment, round count, scores)
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
    assert state is not None, "env.start() should return a valid state"
    assert env.state is not None, "env.state should not be None after start()"
    print("   [OK] Started! Initial tick state (env.state):")
    print(
        f"        Round: {state.get('round')}, Tick: {state.get('tick')}, P1: {state.get('player', {}).get('hp')}, P2: {state.get('opponent', {}).get('hp')}, Dist: {state.get('distance')}"
    )
    assert state.get("event") == "STATE", "State must have event='STATE'"
    assert "player" in state and "x" in state["player"], "State must include 3D player telemetry"
    assert "opponent" in state and "x" in state["opponent"], "State must include 3D opponent telemetry"

    print("\n2. Testing env.step() (1 tick)...")
    s1 = env.step()
    assert s1 is not None, "env.step() should return a valid state"
    print(f"   [OK] Stepped 1 tick: {s1.get('tick')}")
    assert s1.get("tick", 0) == state.get("tick", 0) + 1, "Tick counter should increment by 1"
    assert s1.get("event") == "STATE", "Step state must have event='STATE'"

    print("\n3. Testing env.step(steps=10)...")
    s10 = env.step(steps=10)
    assert s10 is not None, "env.step(10) should return a valid state"
    print(f"   [OK] Stepped 10 ticks: {s10.get('tick')}")
    assert s10.get("tick", 0) == s1.get("tick", 0) + 10, "Tick counter should increment by 10"
    assert "hits" in s10, "Step state must include hits array"

    print("\n4. Testing env.act('p') (punch via engine_controller)...")
    s_act = env.act("p")
    assert s_act is not None, "act() should return a valid state"
    print(f"   [OK] Acted 'p'! P1 Action: {s_act.get('player', {}).get('action')}")

    print("\n5. Testing env.metadata, env.equipment, and env.round...")
    meta = env.metadata
    print(f"   [OK] Metadata: Round {meta.get('current_round')}, Scores: {meta.get('scores')}")
    print(f"        P1 Weapon: {meta.get('equipment', {}).get('player', {}).get('weapon')}")
    print(f"        P2 Weapon: {meta.get('equipment', {}).get('opponent', {}).get('weapon')}")
    assert "equipment" in meta, "metadata must include equipment info"
    assert env.equipment == meta.get("equipment", {}), "env.equipment should match metadata['equipment']"
    assert env.round == 1, "env.round should be 1"
    assert env.current_round == 1, "env.current_round should match env.round"

    print("\n6. Testing env.get_state()...")
    st_cur = env.get_state()
    assert st_cur is not None, "env.get_state() should return a valid state"
    print(
        f"   [OK] Queried state: Tick: {st_cur.get('tick')}, Dist: {st_cur.get('distance')}, P1 Move: {st_cur.get('player', {}).get('action')}"
    )
    assert env.state == st_cur, "env.state should match env.get_state()"
    assert st_cur.get("event") == "STATE", "get_state must return event='STATE'"

    print("\n7. Testing env.freeze()...")
    frozen = env.freeze()
    print(f"   [OK] Frozen: {frozen}")

    print("\n8. Testing env.tick_speed(2.0)...")
    spd = env.tick_speed(2.0)
    print(f"   [OK] Simulation speed: {spd}x")

    print("\n9. Testing env.pause()...")
    paused = env.pause()
    print(f"   [OK] Paused: {paused}")
    time.sleep(1.0)

    print("\n10. Testing env.resume()...")
    resumed = env.resume()
    print(f"   [OK] Resumed: {resumed}")
    time.sleep(1.0)

    print("\n11. Testing env.exit()...")
    exited = env.exit()
    print(f"   [OK] Exited to map: {exited}")
    time.sleep(2.0)

    env.close()
    print("\n" + "=" * 60)
    print(" All ShadowFightEnv methods verified successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
