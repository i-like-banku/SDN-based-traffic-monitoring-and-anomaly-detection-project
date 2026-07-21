"""
run_controller.py
=================
Standalone launcher for the SDN monitoring apps.

On a normal Ryu install you would simply run:

    ryu-manager controller/sdn_monitor.py controller/rest.py

Some environments (notably recent pip builds of the os-ken fork) install the
Python package but omit the ryu-manager / osken-manager console script. This
launcher reproduces what that script does, using the public app_manager API,
so the controller can still be started with:

    python3 run_controller.py                       # loads both default apps
    python3 run_controller.py controller.sdn_monitor controller.rest

The OpenFlow protocol handler (which opens the TCP listener switches connect
to) is always loaded. All application modules are loaded exactly once by
load_apps to avoid duplicate-registration problems.
"""

import os
import sys

# Make both the project root and the controller/ directory importable so that
# `controller.sdn_monitor` and its sibling imports (`store`, `detection`)
# resolve to single, consistent module objects.
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "controller"))
sys.path.insert(0, _ROOT)


def _install_ryu_shim():
    """Alias ryu.* -> os_ken.* when classic Ryu is not installed."""
    try:
        import ryu  # noqa: F401
        return
    except ImportError:
        pass
    import importlib
    import importlib.abc
    import importlib.util

    class _Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, name, path, target=None):
            if name == "ryu" or name.startswith("ryu."):
                try:
                    importlib.import_module("os_ken" + name[3:])
                except ImportError:
                    return None
                return importlib.util.spec_from_loader(name, self)
            return None

        def create_module(self, spec):
            mod = importlib.import_module("os_ken" + spec.name[3:])
            sys.modules[spec.name] = mod
            return mod

        def exec_module(self, module):
            pass

    sys.meta_path.insert(0, _Finder())


def main():
    _install_ryu_shim()

    from ryu.base import app_manager
    from ryu.lib import hub
    from ryu import cfg

    app_modules = sys.argv[1:] or ["controller.sdn_monitor", "controller.rest"]

    cfg.CONF(args=[], project="ryu", prog="run_controller", version="1.0")

    # Reference the OpenFlow handler under the package that is genuinely active
    # (ryu or os_ken) so it is not loaded twice under alias + real names.
    base_pkg = app_manager.__name__.split(".")[0]
    ofp_handler = base_pkg + ".controller.ofp_handler"

    app_mgr = app_manager.AppManager.get_instance()
    app_mgr.load_apps(list(app_modules) + [ofp_handler])
    contexts = app_mgr.create_contexts()
    services = app_mgr.instantiate_apps(**contexts)
    print("SDN monitoring controller running. "
          "OpenFlow on :6653, dashboard on http://localhost:8080/monitor/dashboard")

    try:
        hub.joinall(services)
    except KeyboardInterrupt:
        print("\nshutting down controller...")
    finally:
        app_mgr.close()


if __name__ == "__main__":
    main()
