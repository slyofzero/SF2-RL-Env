#!/usr/bin/env python3
"""
Shadow Fight 2 — Unified RL Environment Interface.

Provides a clean, high-level API to interact with the game engine,
manage simulation timing, control combat flow, and observe game state:

    env = ShadowFightEnv()
    state = env.start()      # Starts fight, freezes ticks, advances 1 tick -> env.state
    env.step()               # Advances 1 tick
    env.step(10)             # Advances 10 ticks
    env.tick_speed(2.0)      # Sets simulation speed
    env.freeze()             # Freezes ticks
    env.get_state()          # Queries state -> env.state
    env.pause()              # Pauses in-game fight
    env.exit()               # Exits to map

CLI / Interactive Console:
    python rl_env/shadow_fight_env.py               # Launches interactive REPL
    python rl_env/shadow_fight_env.py start         # Starts fight and freezes
    python rl_env/shadow_fight_env.py step 10       # Steps 10 ticks
    python rl_env/shadow_fight_env.py state         # Queries current state
    python rl_env/shadow_fight_env.py pause         # Pauses fight
    python rl_env/shadow_fight_env.py exit          # Exits fight to map
"""

import os
import sys
import time
import json
import argparse
from typing import Optional, Dict, Any, Union

from scripts.game_actions import SF2GameActions
from scripts.tick_controller import SF2TickController, ACTION_MAP


class ShadowFightEnv:
    """
    Unified environment for Shadow Fight 2.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.environ.get("FRIDA_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("FRIDA_PORT", "27042"))

        self.actions = SF2GameActions(host=self.host, port=self.port)
        self.clock = SF2TickController(host=self.host, port=self.port)

        self.state: Optional[Dict[str, Any]] = None
        self._is_connected = False

    def connect(self) -> bool:
        """Establishes connections to both game action and tick controller hooks."""
        if not self._is_connected:
            ok_actions = self.actions.connect()
            ok_clock = self.clock.connect()
            self._is_connected = ok_actions and ok_clock
        return self._is_connected

    def start(self, timeout: float = 20.0) -> Dict[str, Any]:
        """
        Starts the fight, freezes game ticks, and advances 1 tick.
        The resulting tick becomes env.state.
        """
        if not self._is_connected:
            self.connect()

        # Arm auto-freeze so physics freezes immediately on round start
        self.clock.enable_auto_freeze(True)

        # Trigger native fight start / restart
        self.actions.start_fight()

        # Wait until round start auto-freeze fires (or timeout)
        frozen = self.clock.wait_for_auto_freeze(timeout=timeout)
        if not frozen:
            # Fallback guarantee: ensure freeze is active
            self.clock.freeze()

        # Advance exactly 1 tick
        self.state = self.clock.step(num_ticks=1)
        return self.state

    def freeze(self) -> bool:
        """Freezes combat physics and match countdown clock in place."""
        if not self._is_connected:
            self.connect()
        frozen = self.clock.freeze()
        self.state = self.clock.get_state()
        return frozen

    def unfreeze(self) -> bool:
        """Unfreezes combat physics back to normal continuous real-time."""
        if not self._is_connected:
            self.connect()
        unfrozen = self.clock.unfreeze()
        self.state = self.clock.get_state()
        return unfrozen

    def step(self, steps: Optional[int] = None, action: Optional[str] = None) -> Dict[str, Any]:
        """
        Advances the simulation by one tick if steps is None, else by 'steps' ticks.
        Optionally dispatches a combat action during the step.
        Updates and returns env.state.
        """
        if not self._is_connected:
            self.connect()

        num_ticks = 1 if steps is None else max(1, int(steps))
        self.state = self.clock.step(num_ticks=num_ticks, action=action)
        return self.state

    def get_state(self) -> Dict[str, Any]:
        """
        Queries the current combat and simulation state without advancing ticks.
        Updates and returns env.state.
        """
        if not self._is_connected:
            self.connect()
        self.state = self.clock.get_state()
        return self.state

    def tick_speed(self, speed: Optional[float] = None) -> float:
        """
        Changes internal simulation speed (e.g. 1.0 = 1x, 2.0 = 2x, 5.0 = 5x).
        If called without arguments, returns the current speed.
        """
        if not self._is_connected:
            self.connect()

        if speed is None:
            cur_state = self.clock.get_state()
            return cur_state.get("speed", 1.0)

        new_speed = self.clock.set_speed(float(speed))
        if self.state:
            self.state["speed"] = new_speed
        return new_speed

    def pause(self) -> bool:
        """Pauses the fight in-engine via the native pause screen."""
        if not self._is_connected:
            self.connect()
        return self.actions.pause()

    def resume(self) -> bool:
        """Resumes the fight from pause in-engine."""
        if not self._is_connected:
            self.connect()
        return self.actions.resume()

    def exit(self) -> bool:
        """Exits the current fight back to the map screen."""
        if not self._is_connected:
            self.connect()
        # Make sure physics is unfrozen so the exit transition animates
        try:
            self.clock.unfreeze()
        except Exception:
            pass
        ok = self.actions.exit_fight()
        self.state = None
        return ok

    def close(self):
        """Cleanly detaches from the game process and restores default state."""
        try:
            if self._is_connected:
                self.clock.unfreeze()
                self.clock.set_speed(1.0)
        except Exception:
            pass
        self.actions.disconnect()
        self.clock.disconnect()
        self._is_connected = False


# Convenient alias
SF2Env = ShadowFightEnv


def format_telemetry_line(st: Dict[str, Any], prefix: str = "") -> str:
    """Formats a telemetry state frame into a concise live status line."""
    tick = st.get('tick', 0)
    clock = st.get('time_left', 0.0)
    p = st.get('player', {}) if isinstance(st.get('player'), dict) else {}
    opp = st.get('opponent', {}) if isinstance(st.get('opponent'), dict) else {}
    p_hp = p.get('hp', st.get('player_hp', 1.0)) * 100
    opp_hp = opp.get('hp', st.get('opponent_hp', 1.0)) * 100
    p_act = p.get('action', 'Idle')
    opp_act = opp.get('action', 'Idle')
    dist = st.get('distance', 0.0)
    hits = st.get('hits', [])
    hits_str = f" | Hits: {len(hits)}" if hits else ""
    return f"{prefix}Tick: {tick:4d} | Clock: {clock:5.1f}s | Dist: {dist:5.1f} | P1: {p_hp:5.1f}% ({p_act}) | P2: {opp_hp:5.1f}% ({opp_act}){hits_str}"


def run_interactive(env: ShadowFightEnv):
    """Interactive command console for maximum environment interaction."""
    st = env.get_state()

    print("\n" + "=" * 80)
    print(" SHADOW FIGHT 2 — UNIFIED RL ENVIRONMENT CONSOLE")
    print("=" * 80)
    in_fight = st.get('in_fight', False)
    frozen = st.get('frozen', False)
    spd = st.get('speed', 1.0)
    print(f" STATUS : In-Fight: {in_fight} | Frozen: {frozen} | Speed: {spd:.1f}x")
    print(f" STATE  : {format_telemetry_line(st)}")
    print("-" * 80)
    print(" Environment Commands:")
    print("   start             -> env.start() (start fight, freeze, step 1)")
    print("   [Enter]           -> env.step() (advance 1 tick)")
    print("   step <N> or <N>   -> env.step(N) (advance N ticks, e.g. '10', 'step 30')")
    print("   <move>            -> Step 6 ticks with combat action (p, k, dp, sp, wp, etc.)")
    print("   freeze / f        -> env.freeze()")
    print("   unfreeze / u      -> env.unfreeze()")
    print("   speed <N>         -> env.tick_speed(N) (e.g. 'speed 2.0')")
    print("   pause             -> env.pause()")
    print("   resume            -> env.resume()")
    print("   exit              -> env.exit() (surrender / back to map)")
    print("   state / status    -> env.get_state() (full telemetry JSON log)")
    print("   q / quit          -> Exit console")
    print("=" * 80 + "\n")

    while True:
        try:
            tag = "FROZEN" if (env.state and env.state.get("frozen")) else "RUNNING"
            cmd = input(f"env [{tag}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            # Advance 1 tick
            st = env.step()
            print(format_telemetry_line(st, prefix=" -> [+1 tick]   "))
            continue

        lower = cmd.lower()
        if lower in ("q", "quit"):
            break
        elif lower == "start":
            print("[*] Starting fight, arming auto-freeze, advancing 1 tick...")
            st = env.start()
            print(f"[OK] Fight started!\n{format_telemetry_line(st, prefix='     ')}")
        elif lower.startswith("step "):
            parts = lower.split()
            if len(parts) >= 2 and parts[1].isdigit():
                n = int(parts[1])
                act = parts[2] if len(parts) >= 3 else None
                st = env.step(steps=n, action=act)
                prefix = f" -> [+{n} ticks] " if not act else f" -> [+{n} {act.upper()}] "
                print(format_telemetry_line(st, prefix=prefix))
        elif lower.isdigit():
            n = int(lower)
            st = env.step(steps=n)
            print(format_telemetry_line(st, prefix=f" -> [+{n} ticks] "))
        elif lower in ("f", "freeze"):
            env.freeze()
            print("[OK] Physics is FROZEN in place.")
        elif lower in ("u", "unfreeze"):
            env.unfreeze()
            print("[OK] Physics is RUNNING continuous 60Hz.")
        elif lower.startswith("speed"):
            parts = lower.split()
            if len(parts) >= 2:
                try:
                    s = env.tick_speed(float(parts[1]))
                    print(f"[OK] Simulation speed set to {s:.1f}x")
                except ValueError:
                    print("[ERROR] Speed must be a number.")
            else:
                print(f"[OK] Current speed: {env.tick_speed():.1f}x")
        elif lower == "pause":
            ok = env.pause()
            print(f"[OK] Pause triggered: {ok}")
        elif lower == "resume":
            ok = env.resume()
            print(f"[OK] Resume triggered: {ok}")
        elif lower == "exit":
            ok = env.exit()
            print(f"[OK] Exit back to map triggered: {ok}")
        elif lower in ("state", "status"):
            st = env.get_state()
            print(json.dumps(st, indent=2))
        elif lower in ACTION_MAP:
            st = env.step(steps=6, action=lower)
            print(format_telemetry_line(st, prefix=f" -> [{lower.upper():4s} 6t]   "))
        else:
            print(f"Unknown command: '{cmd}'. Try 'start', 'step <N>', 'freeze', 'speed <N>', 'pause', 'exit', 'state', 'q'")


def main():
    parser = argparse.ArgumentParser(description="Shadow Fight 2 Unified RL Environment")
    subparsers = parser.add_subparsers(dest="command")

    # Interactive
    subparsers.add_parser("interactive", help="Launch interactive control REPL (default)")

    # start
    subparsers.add_parser("start", help="env.start(): start fight, freeze, step 1 -> env.state")

    # freeze
    subparsers.add_parser("freeze", help="env.freeze(): freeze physics immediately")

    # unfreeze
    subparsers.add_parser("unfreeze", help="env.unfreeze(): resume normal continuous physics")

    # step
    step_p = subparsers.add_parser("step", help="env.step(steps=N, action=...)")
    step_p.add_argument("steps", type=int, nargs="?", default=1, help="Number of ticks to step (default: 1)")
    step_p.add_argument("action", type=str, nargs="?", default=None, help="Action code (e.g. p, k, dp, sp)")

    # speed
    speed_p = subparsers.add_parser("speed", help="env.tick_speed(speed)")
    speed_p.add_argument("scale", type=float, nargs="?", default=None, help="Speed multiplier (default: get current)")

    # pause
    subparsers.add_parser("pause", help="env.pause(): pause in-engine")

    # resume
    subparsers.add_parser("resume", help="env.resume(): resume in-engine")

    # exit
    subparsers.add_parser("exit", help="env.exit(): exit fight to map")

    # state
    subparsers.add_parser("state", help="env.get_state(): print current combat state")

    args = parser.parse_args()

    env = ShadowFightEnv()
    if not env.connect():
        print("[ERROR] Could not connect to game engine.", file=sys.stderr)
        sys.exit(1)

    try:
        if not args.command or args.command == "interactive":
            run_interactive(env)
        elif args.command == "start":
            st = env.start()
            print(json.dumps(st, indent=2))
        elif args.command == "freeze":
            frozen = env.freeze()
            print(f"[SUCCESS] Frozen: {frozen}")
        elif args.command == "unfreeze":
            unfrozen = env.unfreeze()
            print(f"[SUCCESS] Unfrozen: {unfrozen}")
        elif args.command == "step":
            st = env.step(steps=args.steps, action=args.action)
            print(json.dumps(st, indent=2))
        elif args.command == "speed":
            spd = env.tick_speed(args.scale)
            print(f"[SUCCESS] Simulation speed: {spd:.1f}x")
        elif args.command == "pause":
            ok = env.pause()
            print(f"[SUCCESS] Paused: {ok}")
        elif args.command == "resume":
            ok = env.resume()
            print(f"[SUCCESS] Resumed: {ok}")
        elif args.command == "exit":
            ok = env.exit()
            print(f"[SUCCESS] Exited to map: {ok}")
        elif args.command == "state":
            st = env.get_state()
            print(json.dumps(st, indent=2))
    finally:
        if args.command in ("start", "freeze", "step"):
            # If leaving in frozen state from CLI, keep session cleanly
            pass
        elif args.command in ("interactive", "exit"):
            env.close()


if __name__ == "__main__":
    main()
