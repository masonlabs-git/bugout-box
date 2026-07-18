#!/usr/bin/env python3
"""Entry point: python3 run.py            (voice loop)
               python3 run.py --ask "how do I purify water"  (text one-shot)"""
import sys

from box.brain import Brain


def main() -> None:
    brain = Brain()
    if "--ask" in sys.argv:
        q = sys.argv[sys.argv.index("--ask") + 1]
        print(brain.answer(q))
    else:
        brain.loop()


if __name__ == "__main__":
    main()
