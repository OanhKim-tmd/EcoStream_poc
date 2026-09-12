"""Top-level package entrypoint. Launches web dashboard by default or CLI with flags."""

import sys

if len(sys.argv) > 1 and ("--demo" in sys.argv or "--data-dir" in sys.argv or "--help" in sys.argv):
    from ecostream.cli import main
    main()
else:
    from ecostream.app.server import run_server
    run_server()
