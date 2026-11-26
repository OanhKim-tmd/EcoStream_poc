"""Entrypoint: không tham số → web app; có --demo/--input/--run-id → CLI khảo sát."""

import sys

CLI_FLAGS = ("--demo", "--input", "--run-id", "--help", "-h")

if len(sys.argv) > 1 and any(a in CLI_FLAGS for a in sys.argv[1:]):
    from ecostream.cli import main
    sys.exit(main())
else:
    from ecostream.app.server import run_server
    run_server()
