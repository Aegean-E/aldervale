"""ALDERVALE command line entry point.

Exit codes follow the AIKit universal CLI contract: 0 success, 1 operational
failure (with a What/Why/Fix triad on stderr), 2 usage misuse.
"""

import argparse
import sys

from . import __version__


def _build_parser():
    ap = argparse.ArgumentParser(
        prog="aldervale",
        description="ALDERVALE - a 2.5D medieval RPG rendered in tiny ASCII "
                    "cells. Zoom your terminal font out for pixel detail.")
    ap.add_argument("--seed", type=int, default=7,
                    help="world seed (default 7)")
    ap.add_argument("--width", type=int, default=None,
                    help="render width in character cells")
    ap.add_argument("--height", type=int, default=None,
                    help="render height in character cells")
    ap.add_argument("--fps", type=int, default=30,
                    help="frame rate cap (default 30)")
    ap.add_argument("--demo", nargs="?", type=float, const=9.0, metavar="SECS",
                    help="run a non-interactive attract-mode demo and exit")
    ap.add_argument("--benchmark", action="store_true",
                    help="render 60 frames headless and report timing")
    ap.add_argument("--no-color", action="store_true",
                    help="render in monochrome ramp only")
    ap.add_argument("--screenshot", metavar="PATH",
                    help="render one vista frame to a text file and exit")
    ap.add_argument("--save", default="saves/aldervale.json", metavar="PATH",
                    help="save slot path (default saves/aldervale.json)")
    ap.add_argument("--version", action="version",
                    version="ALDERVALE %s" % __version__)
    return ap


def _fail(what, why, fix):
    sys.stderr.write("What: %s\nWhy: %s\nFix: %s\n" % (what, why, fix))
    return 1


def run(argv=None):
    args = _build_parser().parse_args(argv)
    if args.fps < 4 or args.fps > 120:
        return _fail("--fps must be between 4 and 120.",
                     "The frame cap governs simulation stepping.",
                     "Retry with a value in range, e.g. --fps 30.")
    if args.demo is not None and args.demo <= 0:
        return _fail("--demo needs a positive number of seconds.",
                     "The demo mode exits when its timer expires.",
                     "Retry with e.g. --demo 9.")
    if args.width is not None and not 40 <= args.width <= 320:
        return _fail("--width must be between 40 and 320.",
                     "The renderer is sized in character cells.",
                     "Retry with a value in range, e.g. --width 200.")
    if args.height is not None and not 20 <= args.height <= 110:
        return _fail("--height must be between 20 and 110.",
                     "The renderer is sized in character cells.",
                     "Retry with a value in range, e.g. --height 90.")
    from .game import Game
    game = Game(seed=args.seed, width=args.width, height=args.height,
                fps=args.fps, color=not args.no_color,
                demo_secs=args.demo, benchmark=args.benchmark,
                save_path=args.save)
    try:
        if args.screenshot:
            return _screenshot(game, args.screenshot)
        if args.benchmark:
            return _benchmark(game)
        if args.demo is not None and not sys.stdout.isatty():
            return _headless_demo(game, args.demo)
        return _play(game, demo=args.demo)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        return _fail("ALDERVALE stopped: %s" % exc,
                     "An unexpected error occurred inside the engine.",
                     "Report the message above with your terminal and "
                     "Python version.")


def _play(game, demo=None):
    from .term import Terminal

    def progress(model, frac):
        game.term.write("\x1b[2J\x1b[HForging the realm... %3d%%  %s"
                        % (int(frac * 100), model))
        game.term.flush()

    with Terminal(color=game.color) as term:
        term.set_title("ALDERVALE - an ASCII chronicle")
        game.boot(term, progress=progress)
        if demo is not None:
            game.state = "title"
        return game.run()


def _screenshot(game, path):
    """Render one scripted vista to a plain text file (no terminal)."""
    import math

    game.boot(None)
    game.state = "play"
    game._ensure_camera()
    w = game.world
    kx, kz = w.terrain.castle
    game.cam = None
    from .render import Camera, Env, render_scene
    from .buffer import Screen
    from . import hud
    scr = Screen(game.w, game.h, color=game.color)
    cam = Camera(game.w, game.h, kx, kz + 52,
                 w.terrain.height(kx, kz + 52) + 6.0, math.pi, pitch=0.26)
    env = Env(0.24, 12.0)
    render_scene(scr, w, cam, env)
    hud.draw_hud(scr, w, env, 60)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(scr.frame_text() + "\n")
    except OSError as exc:
        return _fail("Cannot write screenshot to %s." % path,
                     "The path is unwritable: %s." % exc,
                     "Choose a writable file path.")
    return 0


def _benchmark(game):
    import time

    t0 = time.monotonic()
    game.boot(None)
    boot_t = time.monotonic() - t0
    game.state = "play"
    game.w, game.h = 132, 60
    game.screen = None
    game.cam = None
    game._open_screen()
    game._ensure_camera()
    from .render import Env
    env = Env(game.world.day_t, 0.0)
    frames = 60
    t0 = time.monotonic()
    for i in range(frames):
        game.world.update(1.0 / 30.0, env)
        game._render(env)
    dt = time.monotonic() - t0
    per = dt / frames * 1000.0
    print("boot %.1fs | %d frames in %.2fs | %.1f ms/frame | ~%d fps cap %d"
          % (boot_t, frames, dt, per, int(1000.0 / per) if per > 0 else 0,
             game.fps_cap))
    return 0


def _headless_demo(game, secs):
    """Non-interactive demo parity for pipes and CI (PRINCIPLE-015)."""
    import time

    game.boot(None)
    game.state = "play"
    game.demo_secs = secs
    game.w, game.h = 100, 46
    game._open_screen()
    game._ensure_camera()
    t_end = time.monotonic() + secs
    from .render import Env
    last = time.monotonic()
    while time.monotonic() < t_end:
        now = time.monotonic()
        dt = min(0.05, now - last)
        last = now
        game.cam_yaw += dt * 0.2
        env = Env(game.world.day_t, game.world.time)
        game.world.update(dt, env)
        game._render(env)
    print("demo: %ds headless, %d entities, quest=%s" %
          (int(secs), len(game.world.entities), game.world.quest))
    return 0


if __name__ == "__main__":
    sys.exit(run())
